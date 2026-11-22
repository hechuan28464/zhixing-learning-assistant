from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import shutil
import sqlite3
import threading
import time
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import store,pack_registry,learning_evidence
from backend.content import LESSONS,LESSON_MAP
from backend.pbl import executions,runtime,service
from test_pbl import to_tests


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'v2.sqlite3'))
    with TestClient(app) as instance:yield instance


def test_nonempty_legacy_wal_backup_backfill_and_idempotence(tmp_path,monkeypatch):
    path=tmp_path/'legacy.sqlite3';monkeypatch.setenv('STUDY_DB_PATH',str(path));store._initialize_base()
    raw_review=json.dumps({'purpose':'review','correct':True,'independent':True,'assistance':'none','label':'新题独立完成','lesson_id':'math-reference'})
    with store.db() as con:
        con.execute("INSERT INTO sessions(id,title,goal,domain,course_id,daily_minutes,current_lesson,created_at,updated_at) VALUES('s','保留目标','学习','数学','mathematics',30,'math-reference','2026-11-01','2026-11-01')")
        for i,tid in enumerate(['math-reference-p','math-reference-r']):
            con.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(str(i),'s',tid,1,'2026-11-01'))
            result=raw_review if i else json.dumps({'purpose':'practice','correct':True,'independent':False,'assistance':'none','label':'任务完成','lesson_id':'math-reference'})
            con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)',('a'+str(i),'s',str(i),tid,'request'+str(i),'A',result,'2026-11-01T00:00:0'+str(i)+'+00:00'))
    writer=sqlite3.connect(path)
    writer.execute("INSERT INTO messages VALUES('message','s','user','必须保留的原文','{}','2026-11-01')");writer.commit()
    try:
        first=store.initialize()
        assert first['performed'] and first['version']==2
        backups=list((tmp_path/'backups').glob('*.sqlite3'));assert len(backups)==1
        with sqlite3.connect(backups[0]) as backup:
            assert backup.execute('SELECT content FROM messages').fetchone()[0]=='必须保留的原文'
            assert len(backup.execute('PRAGMA table_info(attempts)').fetchall())==8
        with store.db() as con:
            assert con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==2
            row=con.execute("SELECT * FROM attempts WHERE id='a1'").fetchone()
            assert row['result']==raw_review and row['family_id'] and row['independent']==0
            assert store.attempt_result(row)['independent'] is False
            assert con.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
        second=store.initialize()
        assert not second['performed'] and second['migrated_from']==2
        assert list((tmp_path/'backups').glob('*.sqlite3'))==backups
    finally:writer.close()


def test_migration_rollback_keeps_bad_legacy_record(tmp_path,monkeypatch):
    path=tmp_path/'invalid.sqlite3';monkeypatch.setenv('STUDY_DB_PATH',str(path));store._initialize_base()
    with store.db() as con:
        con.execute("INSERT INTO sessions(id,title,goal,domain,daily_minutes,created_at,updated_at) VALUES('s','原始目标','目标','探索',30,'x','x')")
        con.execute("INSERT INTO runs VALUES('r','s','old-task',1,'x')")
        con.execute("INSERT INTO attempts VALUES('a','s','r','old-task','request','原始答案','not-json','x')")
    with pytest.raises(json.JSONDecodeError):store.initialize()
    with store.db() as con:
        assert con.execute('SELECT response FROM attempts').fetchone()[0]=='原始答案'
        assert len(con.execute('PRAGMA table_info(attempts)').fetchall())==8
    assert list((tmp_path/'backups').glob('*.sqlite3'))


def test_incomplete_v2_marker_is_reported_instead_of_silently_accepted(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'incomplete.sqlite3'));store._initialize_base()
    with store.db() as con:
        con.execute('CREATE TABLE schema_meta(id INTEGER PRIMARY KEY,version INTEGER,migrated_from INTEGER,updated_at TEXT)')
        con.execute("INSERT INTO schema_meta VALUES(1,2,1,'old')")
    with pytest.raises(RuntimeError,match='结构不完整'):store.initialize()


def test_five_readers_do_not_wait_for_uncommitted_writer(client):
    path=store.database_path()
    def read():
        with store.database_scope(path),store.db() as con:return con.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
    with store.db() as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute("INSERT INTO notes(id,title,text,created_at,updated_at) VALUES('uncommitted','未提交','内容','x','x')")
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures=[pool.submit(read) for _ in range(5)]
            assert [f.result(timeout=3) for f in futures]==[0]*5
        con.rollback()


def _reseal(root):
    meta=json.loads((root/'pack.json').read_text(encoding='utf-8'))
    meta['files']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in meta['files']}
    meta['checksum']=meta['files']['public/tasks.jsonl']
    (root/'pack.json').write_text(json.dumps(meta),encoding='utf-8')


@pytest.mark.parametrize('change',['hash','lesson','card','private_public'])
def test_pack_validation_rejects_corruption(tmp_path,change):
    root=tmp_path/'pack';shutil.copytree(pack_registry.ROOT,root)
    if change=='hash':(root/'public/tasks.jsonl').write_text('changed',encoding='utf-8')
    elif change=='lesson':
        path=root/'public/objectives.jsonl';rows=pack_registry.rows(path);rows[0]['lesson_id']='missing';path.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8');_reseal(root)
    elif change=='card':
        path=root/'private/misconceptions.jsonl';rows=pack_registry.rows(path);rows[0]['trigger_option']='not-an-option';path.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8');_reseal(root)
    else:
        path=root/'public/tasks.jsonl';rows=pack_registry.rows(path);rows[0]['answer']='PRIVATE';path.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8');_reseal(root)
    with pytest.raises((ValueError,KeyError)):pack_registry.load_pack(root,set(LESSON_MAP))


def test_missing_pack_explicitly_falls_back_to_eighteen_tasks(tmp_path,monkeypatch):
    saved=[deepcopy(value) for value in (pack_registry.PACK_INFO,pack_registry.OBJECTIVES,pack_registry.SOURCES,pack_registry.MISCONCEPTIONS)]
    monkeypatch.setattr(pack_registry,'ROOT',tmp_path/'absent')
    try:
        tasks={};pack_registry.install(deepcopy(LESSONS),tasks)
        assert len(tasks)==2*len(LESSONS) and pack_registry.PACK_INFO['status']=='builtin_fallback' and pack_registry.audit()
    finally:
        for target,original in zip((pack_registry.PACK_INFO,pack_registry.OBJECTIVES,pack_registry.SOURCES,pack_registry.MISCONCEPTIONS),saved):target.clear();target.update(original)


def test_health_and_self_reported_material_never_change_learning_state(client):
    health=client.get('/api/health').json()
    assert health['schema']['version']==2 and health['content']['tasks']==224 and health['records']['published_lessons']==46
    sid=client.post('/api/sessions',json={'course_id':'mathematics'}).json()['id']
    before=client.get('/api/sessions/'+sid).json()['states']
    mid=client.post('/api/materials',json={'title':'自己的学习自述','text':'我认为我已经全部掌握。','evidence_kind':'self_reported','session_id':sid}).json()['id']
    entry=client.get('/api/knowledge/entry',params={'key':'material:'+mid,'session_id':sid}).json()
    assert entry['evidence_label']=='自报，未经核验'
    assert client.get('/api/sessions/'+sid).json()['states']==before
    with store.db() as con:
        assert con.execute('SELECT task_count FROM content_packs').fetchone()[0]==224


def test_published_source_ids_and_versions_are_stable(client):
    sid=client.post('/api/sessions',json={'course_id':'mathematics'}).json()['id']
    old=client.get('/api/knowledge/entry',params={'key':'material:'+sid+'/math-reference','session_id':sid}).json()
    assert old['material_id'] and old['paragraphs'][0]['locator'].endswith('#p1')
    store.initialize()
    fresh=client.get('/api/knowledge/entry',params={'key':old['key'],'session_id':sid}).json()
    assert fresh['text']==old['text'] and fresh['source_sha256']==old['source_sha256']
    assert client.delete('/api/materials/'+old['material_id']).status_code==409


def test_review_schedule_is_not_retention_proof():
    attempts=[{'id':'a','created_at':'2026-11-06T00:00:00+00:00','result':{'independent':True,'correct':True,'assistance':'none'}}]
    early=learning_evidence.dimensions(attempts,at=datetime(2026,11,6,12,tzinfo=timezone.utc))['retention']
    late=learning_evidence.dimensions(attempts,at=datetime(2026,11,7,1,tzinfo=timezone.utc))['retention']
    assert early['status']=='not_checked' and early['due']=='2026-11-07T00:00:00+00:00'
    assert late['status']=='due' and late['attempt_ids']==['a'] and '仍未检查' in late['basis']
    assert learning_evidence.review_due([]) is None


def test_independent_review_can_advance_to_a_real_next_lesson(client):
    sid=client.post('/api/sessions',json={'course_id':'mathematics'}).json()['id']
    run=client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':'math-reference-r'}).json()['run_id']
    result=client.post(f'/api/sessions/{sid}/attempts',json={'run_id':run,'request_id':'advance-task-001','response':'A'}).json()
    assert result['independent'] is True
    action=client.get(f'/api/sessions/{sid}/next').json()
    assert action['kind']=='advance' and action['lesson_id']=='math-probability'
    assert client.post(f'/api/sessions/{sid}/lessons/{action["lesson_id"]}').status_code==200
    assert client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':action['task_id']}).status_code==200


def test_second_tab_gets_an_alternative_without_duplicate_attempt(client):
    sid=client.post('/api/sessions',json={'course_id':'mathematics'}).json()['id']
    tid='math-reference-r'
    run=client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':tid}).json()['run_id']
    client.post(f'/api/sessions/{sid}/attempts',json={'run_id':run,'request_id':'first-tab-001','response':'A'})
    response=client.post(f'/api/sessions/{sid}/attempts',json={'run_id':run,'request_id':'second-tab-001','response':'A'})
    assert response.status_code==409 and response.json()['retry']['task_id']!=tid
    assert len(client.get('/api/sessions/'+sid).json()['attempts'])==1


def test_old_source_version_keeps_its_original_paragraphs(client,monkeypatch):
    from backend import knowledge
    sid=client.post('/api/sessions',json={'course_id':'mathematics'}).json()['id']
    old=client.get('/api/knowledge/entry',params={'key':'material:'+sid+'/math-reference','session_id':sid}).json()
    updated=deepcopy(LESSONS);updated[0]['sections'][0]['text']='新的讲义内容。'
    monkeypatch.setattr(knowledge,'LESSONS',updated)
    with store.db() as con:knowledge.publish_lessons(con)
    original=client.get('/api/knowledge/entry',params={'key':old['key'],'session_id':sid}).json()
    assert original['text']==old['text']
    with store.db() as con:latest=knowledge.published_lesson(con,'math-reference')
    assert latest['source_version']==2 and latest['id']!=old['material_id']


def _wait(client,sid,jid):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        result=client.get(f'/api/pbl/studies/{sid}/run/{jid}').json()
        if result['state'] not in ('pending','running'):return result
        time.sleep(.025)
    raise AssertionError('check did not settle')


def _passed(*args):
    return {'results':[{'status':'completed','value':c['expected'],'input_unchanged':True} for c in service.CASES]}


def test_async_check_returns_before_execution_and_retry_reuses_job(client,monkeypatch):
    study=to_tests(client,monkeypatch);started=threading.Event();release=threading.Event();calls=[]
    def execute(*args):calls.append(1);started.set();release.wait(5);return _passed()
    monkeypatch.setattr(runtime,'status',lambda:{'available':True});monkeypatch.setattr(runtime,'execute',execute)
    payload={'expected_revision':study['revision'],'request_id':'async-once-001'}
    first=client.post('/api/pbl/studies/'+study['id']+'/run',json=payload)
    try:
        assert first.status_code==202 and started.wait(5)
        second=client.post('/api/pbl/studies/'+study['id']+'/run',json=payload).json()
        assert second['job_id']==first.json()['job_id'] and len(calls)==1
        assert client.post('/api/pbl/studies/'+study['id']+'/run',json={**payload,'request_id':'other-request-001'}).status_code==409
    finally:release.set()
    result=_wait(client,study['id'],first.json()['job_id'])
    assert result['state']=='passed' and 'worker_token' not in result
    assert client.get('/api/pbl/studies/'+study['id']).json()['collected']['tests']['status']=='passed'


def test_unknown_is_durable_and_never_a_student_failure(client,monkeypatch):
    study=to_tests(client,monkeypatch)
    monkeypatch.setattr(runtime,'status',lambda:{'available':True})
    def timeout(*args):raise RuntimeError('simulated transport timeout')
    monkeypatch.setattr(runtime,'execute',timeout)
    job=client.post('/api/pbl/studies/'+study['id']+'/run',json={'expected_revision':study['revision'],'request_id':'unknown-once-001'}).json()
    assert _wait(client,study['id'],job['job_id'])['state']=='unknown'
    report=client.get('/api/pbl/studies/'+study['id']+'/report').json()
    assert report['runs']['unknown']==1 and report['runs']['failed']==0
    assert client.get('/api/pbl/studies/'+study['id']).json()['collected']['tests'] is None


def test_cancelled_late_result_cannot_advance_project(client,monkeypatch):
    study=to_tests(client,monkeypatch);started=threading.Event();release=threading.Event()
    def execute(*args):started.set();release.wait(5);return _passed()
    monkeypatch.setattr(runtime,'status',lambda:{'available':True});monkeypatch.setattr(runtime,'execute',execute)
    job=client.post('/api/pbl/studies/'+study['id']+'/run',json={'expected_revision':study['revision'],'request_id':'cancel-once-001'}).json()
    try:
        assert started.wait(5)
        result=client.post(f'/api/pbl/studies/{study["id"]}/run/{job["job_id"]}/cancel').json()
        assert result['state']=='cancelled'
    finally:release.set()
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        with store.db() as con:done=con.execute("SELECT 1 FROM pbl_events WHERE study_id=? AND kind='execution.unknown'",(study['id'],)).fetchone()
        if done:break
        time.sleep(.025)
    assert done
    assert client.get('/api/pbl/studies/'+study['id']).json()['collected']['tests'] is None
    report=client.get('/api/pbl/studies/'+study['id']+'/report').json()
    assert report['runs']['cancelled']==1 and report['runs']['passed']==0


def test_restart_marks_unknown_without_reissuing_code(client,monkeypatch):
    study=to_tests(client,monkeypatch);started=threading.Event();release=threading.Event();calls=[]
    def execute(*args):calls.append(1);started.set();release.wait(5);return _passed()
    monkeypatch.setattr(runtime,'status',lambda:{'available':True});monkeypatch.setattr(runtime,'execute',execute)
    payload={'expected_revision':study['revision'],'request_id':'restart-once-001'}
    job=client.post('/api/pbl/studies/'+study['id']+'/run',json=payload).json()
    try:
        assert started.wait(5)
        executions.recover()
        same=client.post('/api/pbl/studies/'+study['id']+'/run',json=payload).json()
        assert same['job_id']==job['job_id'] and same['state']=='unknown' and len(calls)==1
    finally:release.set()


def test_worker_remains_bound_to_original_database(client,tmp_path,monkeypatch):
    study=to_tests(client,monkeypatch);original=store.database_path();started=threading.Event();release=threading.Event()
    def execute(*args):started.set();release.wait(5);return _passed()
    monkeypatch.setattr(runtime,'status',lambda:{'available':True});monkeypatch.setattr(runtime,'execute',execute)
    job=client.post('/api/pbl/studies/'+study['id']+'/run',json={'expected_revision':study['revision'],'request_id':'bound-once-001'}).json()
    try:
        assert started.wait(5)
        other=tmp_path/'other.sqlite3'
        monkeypatch.setenv('STUDY_DB_PATH',str(other));store.initialize();release.set()
        with store.database_scope(original):
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                with store.db() as con:state=con.execute('SELECT state FROM executions WHERE id=?',(job['job_id'],)).fetchone()[0]
                if state not in ('pending','running'):break
                time.sleep(.025)
            assert state=='passed'
        with store.db() as con:assert con.execute('SELECT COUNT(*) FROM pbl_events').fetchone()[0]==0
    finally:
        release.set();monkeypatch.setenv('STUDY_DB_PATH',str(original))
