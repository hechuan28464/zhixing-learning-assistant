import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.pbl import service,runtime
from backend.pbl.engine import transition,PROJECT

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'pbl.sqlite3'))
    monkeypatch.delenv('STUDY_PBL_RUNNER_URL',raising=False)
    monkeypatch.delenv('STUDY_PBL_RUNNER_TOKEN',raising=False)
    with TestClient(app) as client:yield client

def start(client):return client.post('/api/pbl/studies',json={'request_id':'pbl-start-test-01'}).json()

def act(client,study,kind,**fields):
    result=client.post('/api/pbl/studies/'+study['id']+'/commands',json={'kind':kind,'expected_revision':study['revision'],'request_id':'pbl-action-'+str(study['revision'])+'-'+kind,**fields})
    assert result.status_code==200,result.text
    return result.json()

def review(client,study,kind,monkeypatch):
    monkeypatch.setattr(service.agent,'call_model',lambda *args,**kwargs:({'content':'这是测试固定回复：检查输入、累计规则及空记录处理。'},{'model':'fixture'}))
    result=client.post('/api/pbl/studies/'+study['id']+'/chat',json={'request_id':'pbl-review-'+str(study['revision']),'review_kind':kind,'artifact_sha':study['artifacts'][kind]['sha256'],'message':'请审阅当前保存版本'})
    assert result.status_code==200,result.text
    return result.json()

def to_tests(client,monkeypatch):
    study=start(client)
    study=act(client,study,'next',text='循环读取每条记录，用主题作为键累计分钟数。')
    study=act(client,study,'decision',chosen='每条记录使用字典表示',rationale='这样可以明确区分主题和分钟数。')
    study=act(client,study,'next')
    study=act(client,study,'plan',text='输入记录列表，逐条读取并累计主题时长，返回新字典，检查空输入。')
    study=review(client,study,'plan',monkeypatch)
    study=act(client,study,'next',artifact_sha=study['artifacts']['plan']['sha256'])
    study=act(client,study,'code',text='def summarize(records):\n    return {}\n')
    study=review(client,study,'code',monkeypatch)
    return act(client,study,'next',artifact_sha=study['artifacts']['code']['sha256'])

def test_upstream_contract_is_real_seven_step_state_machine():
    state=transition('start')['state']
    with pytest.raises(service.learning.Conflict):transition('next',state)
    assert len(PROJECT['milestones'][0]['stages'])==7

def test_catalog_is_read_only_and_has_no_answer_keys(client):
    data=client.get('/api/pbl/catalog').json()
    assert not data['studies'] and not data['runtime']['available']
    assert all('answer' not in q and 'explain' not in q for q in data['project']['quiz'])
    assert not client.get('/api/bootstrap').json()['sessions']

def test_start_is_unique_and_resumable(client):
    first=start(client);again=start(client)
    assert first['id']==again['id'] and first['stage']==0
    assert len(client.get('/api/bootstrap').json()['sessions'])==1

def test_stage_gates_and_command_retry(client):
    study=start(client);url='/api/pbl/studies/'+study['id']+'/commands'
    assert client.post(url,json={'kind':'next','expected_revision':1,'request_id':'missing-explanation'}).status_code==400
    payload={'kind':'next','text':'按主题累计每条学习记录的分钟数。','expected_revision':1,'request_id':'pbl-retry-fixed-01'}
    first=client.post(url,json=payload);again=client.post(url,json=payload)
    assert first.status_code==again.status_code==200
    assert first.json()['revision']==again.json()['revision'] and again.json()['stage']==1
    assert client.post(url,json={**payload,'text':'不同内容'}).status_code==409
    assert client.post(url,json={'kind':'next','expected_revision':2,'request_id':'missing-decision'}).status_code==409

def test_review_is_bound_to_saved_artifact(client,monkeypatch):
    study=start(client);study=act(client,study,'next',text='先读取主题，再累计分钟数。');study=act(client,study,'decision',chosen='使用字典',rationale='字段名称清晰');study=act(client,study,'next')
    study=act(client,study,'plan',text='第一版计划：用字典累计主题分钟数。');old_hash=study['artifacts']['plan']['sha256'];study=review(client,study,'plan',monkeypatch)
    assert study['reviews']['plan']
    study=act(client,study,'plan',text='第二版计划：还要检查空输入，返回新字典。')
    assert not study['reviews']['plan']
    result=client.post('/api/pbl/studies/'+study['id']+'/commands',json={'kind':'next','expected_revision':study['revision'],'artifact_sha':old_hash,'request_id':'stale-approval-test'})
    assert result.status_code==409

def test_unconfigured_executor_does_not_make_test_results(client,monkeypatch):
    study=to_tests(client,monkeypatch)
    result=client.post('/api/pbl/studies/'+study['id']+'/evaluate',json={'expected_revision':study['revision'],'request_id':'no-execution-test'})
    assert result.status_code==503
    saved=client.get('/api/pbl/studies/'+study['id']).json()
    assert saved['stage']==4 and saved['collected']['tests'] is None

def test_fixture_execution_result_is_checked_on_host_and_old_results_invalidated(client,monkeypatch):
    study=to_tests(client,monkeypatch)
    monkeypatch.setattr(runtime,'status',lambda:{'available':True,'label':'测试夹具执行器'})
    monkeypatch.setattr(runtime,'execute',lambda source,inputs:{'results':[{'status':'completed','value':{},'input_unchanged':True} for _ in inputs]})
    result=client.post('/api/pbl/studies/'+study['id']+'/evaluate',json={'expected_revision':study['revision'],'request_id':'fixture-failed-run'})
    assert result.status_code==200
    study=result.json();assert study['collected']['tests']['status']=='failed'
    study=act(client,study,'code',text='def summarize(records):\n    return dict()\n')
    assert study['collected']['tests'] is None

def test_infrastructure_error_is_not_a_student_failure(client,monkeypatch):
    study=to_tests(client,monkeypatch)
    monkeypatch.setattr(runtime,'status',lambda:{'available':True})
    monkeypatch.setattr(runtime,'execute',lambda *args:{'results':[{'status':'infrastructure'}]*3})
    result=client.post('/api/pbl/studies/'+study['id']+'/evaluate',json={'expected_revision':study['revision'],'request_id':'fixture-infra-error'})
    assert result.status_code==503
    assert client.get('/api/pbl/studies/'+study['id']).json()['collected']['tests'] is None
    report=client.get('/api/pbl/studies/'+study['id']+'/report').json()
    assert report['runs']['unknown']==1 and report['runs']['failed']==0
    assert report['checks'][0]['state']=='unknown'

def test_private_fixture_can_complete_gates_without_claiming_live_execution(client,monkeypatch):
    study=to_tests(client,monkeypatch)
    monkeypatch.setattr(runtime,'status',lambda:{'available':True,'label':'test fixture'})
    monkeypatch.setattr(runtime,'execute',lambda *args:{'results':[{'status':'completed','value':c['expected'],'input_unchanged':True} for c in service.CASES]})
    study=client.post('/api/pbl/studies/'+study['id']+'/evaluate',json={'expected_revision':study['revision'],'request_id':'fixture-pass-run'}).json()
    study=act(client,study,'next');study=act(client,study,'quiz',answers=[1,1]);study=act(client,study,'next');study=act(client,study,'next',text='通过空输入与重复主题检查了我的累计规则。')
    assert study['status']=='completed'
    assert client.post('/api/pbl/studies/'+study['id']+'/commands',json={'kind':'next','expected_revision':study['revision'],'text':'重复完成','request_id':'duplicate-completion'}).status_code==409

def test_project_artifacts_are_saved_without_running_source(client):
    study=start(client)
    result=client.post('/api/pbl/studies/'+study['id']+'/commands',json={'kind':'code','text':'raise RuntimeError("must not execute on host")','expected_revision':1,'request_id':'wrong-stage-code'})
    assert result.status_code==409

def test_artifact_versions_are_citable_and_included_in_export(client):
    study=start(client);study=act(client,study,'next',text='用循环累计每个主题的分钟数。');study=act(client,study,'decision',chosen='字典列表',rationale='主题和分钟数字段清晰');study=act(client,study,'next')
    study=act(client,study,'plan',text='计划第一版：按主题累计分钟数。')
    first=client.get('/api/knowledge',params={'kind':'record','session_id':study['session_id']}).json()['items'][0]
    study=act(client,study,'plan',text='计划第二版：另需检查空记录。')
    original=client.get('/api/knowledge/entry',params={'key':first['key']}).json()
    assert original['text']=='计划第一版：按主题累计分钟数。'
    exported=client.get('/api/export').json()['data']['pbl']
    assert len(exported['artifact_versions'])==2
    assert '计划第二版' in client.get('/api/export/markdown').text

def test_late_model_review_cannot_approve_newer_artifact(client,monkeypatch):
    study=start(client);study=act(client,study,'next',text='按主题保留累计值。');study=act(client,study,'decision',chosen='使用字典',rationale='主题可作为键');study=act(client,study,'next');study=act(client,study,'plan',text='最初计划：读取记录累计。')
    def late_model(*args,**kwargs):
        act(client,study,'plan',text='新计划：明确空记录返回新字典。')
        return {'content':'旧计划的审阅建议。'},{'model':'fixture'}
    monkeypatch.setattr(service.agent,'call_model',late_model)
    reviewed=client.post('/api/pbl/studies/'+study['id']+'/chat',json={'request_id':'pbl-late-review-01','review_kind':'plan','artifact_sha':study['artifacts']['plan']['sha256'],'message':'请审阅'}).json()
    assert not reviewed['reviews']['plan']
    assert reviewed['messages'][-1]['metadata']['review_accepted'] is False

def test_project_ai_help_is_acknowledged_before_counting_as_delivered(client,monkeypatch):
    from backend.store import db
    session=client.post('/api/sessions',json={'course_id':'programming'}).json()
    run=client.post('/api/sessions/'+session['id']+'/tasks/open',json={'task_id':'python-variable-p'}).json()
    study=start(client);study=act(client,study,'next',text='逐条读取并累计分钟数。');study=act(client,study,'decision',chosen='字典列表',rationale='字段含义明确');study=act(client,study,'next');study=act(client,study,'plan',text='按主题累计时长，并检查空输入。')
    study=review(client,study,'plan',monkeypatch)
    aid=study['messages'][-1]['metadata']['assistance_id']
    with db() as con:assert con.execute('SELECT delivery FROM assistance WHERE id=?',(aid,)).fetchone()[0]=='offered'
    assert client.post('/api/sessions/'+session['id']+'/assistance/'+aid+'/ack').status_code==200
    result=client.post('/api/sessions/'+session['id']+'/attempts',json={'run_id':run['run_id'],'response':'B','request_id':'pbl-assisted-task-01'}).json()
    assert result['assistance']!='none' and not result['independent']
