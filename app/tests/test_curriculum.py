import json,zipfile,hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import store
from backend.content import LESSONS,TASK_MAP,LESSON_MAP
from backend.curriculum_20261109 import UNITS,REFERENCES,ordered_question
from backend.packs import PACK_INFO

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'curriculum.sqlite3'))
    with TestClient(app) as c:yield c

def submit(c,sid,tid,answer,key):
    opened=c.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':tid})
    assert opened.status_code==200,opened.text
    result=c.post(f'/api/sessions/{sid}/attempts',json={'run_id':opened.json()['run_id'],'response':answer,'request_id':key})
    assert result.status_code==200,result.text
    return result.json()

def test_real_curriculum_counts_references_and_full_chapter_mapping(client):
    expected={'programming':(20,17),'mathematics':(16,13),'reading':(10,7)}
    assert PACK_INFO['status']=='loaded' and PACK_INFO['task_count']==224
    for course,(count,chapters) in expected.items():
        data=client.get('/api/catalog/'+course).json()
        assert data['lesson_count']==count and len(data['lessons'])==count
        assert sorted(l['chapter'] for l in data['lessons'] if l.get('chapter'))==list(range(1,chapters+1))
        assert data['reference']['url'].startswith('https://')
        for lesson in data['lessons']:
            for task in lesson['tasks']:
                assert not {'answer','hint','explanation','misconception_by_option'}&task.keys()
            if lesson.get('chapter'):
                assert len(lesson['sections'])>=4 and sum(len(p['text']) for p in lesson['sections'])>=240
                assert {t['purpose'] for t in lesson['tasks']}=={'diagnostic','practice','review','remediation','reflection'}
    assert REFERENCES['programming']['isbn']=='9787302590101'

@pytest.mark.parametrize('course,lid',[('programming','py-ch17'),('mathematics','stat-ch08'),('reading','crit-ch06')])
def test_diagnostic_personalization_remedy_review_and_open_answer(client,course,lid):
    sid=client.post('/api/sessions',json={'course_id':course}).json()['id']
    client.post(f'/api/sessions/{sid}/lessons/{lid}')
    next_=client.get(f'/api/sessions/{sid}/next').json();assert next_['task_id']==lid+'-diagnostic'
    task=TASK_MAP[next_['task_id']][1];wrong=next(o['id'] for o in task['options'] if o['id']!=task['answer'])
    result=submit(client,sid,task['id'],wrong,lid+'-wrong-diagnostic')
    assert result['diagnosis']['remedy_task_id']==lid+'-remediation'
    next_=client.get(f'/api/sessions/{sid}/next').json();assert next_['kind']=='remedy'
    remedy=TASK_MAP[next_['task_id']][1];submit(client,sid,remedy['id'],remedy['answer'],lid+'-guided-remedy')
    review=TASK_MAP[lid+'-review'][1];result=submit(client,sid,review['id'],review['answer'],lid+'-fresh-review')
    assert result['independent'] is True and result['correct'] is True
    coverage=client.get(f'/api/sessions/{sid}/evidence').json()['lessons'][lid]['dimensions']['coverage']
    assert coverage['objectives']=={'total':3,'covered':1}
    result=submit(client,sid,lid+'-reflection','我保留原始条件，逐项核对例子、依据与结论范围。',lid+'-reflection')
    assert result['correct'] is None and result['status']=='pending_review'

def test_correct_diagnosis_offers_fresh_review_without_mandatory_repetition(client):
    sid=client.post('/api/sessions',json={'course_id':'programming'}).json()['id'];lid='py-ch04'
    client.post(f'/api/sessions/{sid}/lessons/{lid}')
    t=TASK_MAP[lid+'-diagnostic'][1];submit(client,sid,t['id'],t['answer'],'correct-diag-route')
    next_=client.get(f'/api/sessions/{sid}/next').json()
    assert next_['kind']=='review' and next_['task_id']==lid+'-review'
    assert client.get(f'/api/sessions/{sid}').json()['states'][lid]['status']!='independent'

def test_old_task_contracts_and_ids_are_unchanged():
    backup=Path(__file__).resolve().parents[1]/'.qa/curriculum-before-20261109.zip'
    if not backup.exists():pytest.skip('Local migration snapshot is unavailable')
    root=Path(__file__).resolve().parents[1]/'backend/resources/contest-pack-v1'
    with zipfile.ZipFile(backup) as z:
        for name,key in [('public/tasks.jsonl','id'),('private/assessment_contracts.jsonl','task_id'),('public/lessons.jsonl','id')]:
            old=[json.loads(line) for line in z.read(name).decode().splitlines() if line.strip()]
            current={row[key]:row for row in map(json.loads,(root/name).read_text(encoding='utf-8').splitlines())}
            assert all(current[row[key]]==row for row in old)

def test_option_order_is_stable_and_not_a_course_wide_answer_pattern():
    answers=[]
    for unit in UNITS:
        for purpose,index in [('diagnostic',0),('practice',1),('review',2)]:
            q=ordered_question(unit['id'],purpose,unit['questions'][index])
            assert q==ordered_question(unit['id'],purpose,unit['questions'][index])
            assert q['options'][ord(q['answer'])-65]==unit['questions'][index]['options'][ord(unit['questions'][index]['answer'])-65]
        answers.append(TASK_MAP[unit['id']+'-review'][1]['answer'])
    assert set(answers)=={'A','B','C'} and max(answers.count(x) for x in 'ABC')<len(answers)*.6
