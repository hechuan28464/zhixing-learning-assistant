import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.content import TASK_MAP
from backend.packs import MISCONCEPTIONS


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'competition.sqlite3'))
    with TestClient(app) as instance:yield instance


@pytest.mark.parametrize('task_id',sorted(TASK_MAP))
def test_all_registered_tasks_are_openable_without_private_contract(client,task_id):
    lesson,_,purpose=TASK_MAP[task_id]
    sid=client.post('/api/sessions',json={'course_id':lesson['course_id']}).json()['id']
    opened=client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':task_id})
    assert opened.status_code==200
    payload=opened.json()
    assert payload['purpose']==purpose
    assert not {'answer','hint','explanation','misconception_by_option','evaluation'}&set(payload['task'])


@pytest.mark.parametrize('task_id,option',sorted(MISCONCEPTIONS))
def test_wrong_diagnosis_leads_to_bound_remediation_and_real_evidence(client,task_id,option):
    lesson=TASK_MAP[task_id][0];card=MISCONCEPTIONS[(task_id,option)]
    sid=client.post('/api/sessions',json={'course_id':lesson['course_id']}).json()['id']
    client.post(f'/api/sessions/{sid}/lessons/{lesson["id"]}')
    run=client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':task_id}).json()['run_id']
    result=client.post(f'/api/sessions/{sid}/attempts',json={'run_id':run,'response':option,'request_id':'diagnosis-request-001'}).json()
    assert result['diagnosis']['remedy_task_id']==card['remediation_task_id']
    step=client.get(f'/api/sessions/{sid}/next').json()
    assert step['kind']=='remedy' and step['task_id']==card['remediation_task_id']
    evidence=client.get(f'/api/sessions/{sid}/evidence').json()['lessons'][lesson['id']]
    assert evidence['dimensions']['retention']['status']=='not_checked'
    assert evidence['attempts'][0]['id']==result['attempt_id']
    graph=client.get(f'/api/sessions/{sid}/graph').json()
    node=next(n for n in graph['nodes'] if n.get('lesson_id')==lesson['id'])
    assert node['evidence_count']==1 and node['evidence'][0]['id']==result['attempt_id']
    assert client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':step['task_id']}).status_code==200


def test_exposed_family_cannot_become_independent_by_changing_task_id(client):
    sid=client.post('/api/sessions',json={'course_id':'mathematics'}).json()['id']
    for index,tid in enumerate(['math-reference-p','math-reference-r']):
        run=client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':tid}).json()['run_id']
        result=client.post(f'/api/sessions/{sid}/attempts',json={'run_id':run,'response':TASK_MAP[tid][1]['answer'],'request_id':'family-request-'+str(index)}).json()
    assert result['correct'] is True and result['independent'] is False


def test_assisted_remediation_prefers_a_review_instead_of_repeating_practice(client):
    sid=client.post('/api/sessions',json={'course_id':'mathematics'}).json()['id']
    tid='math-reference-remedy-20261106'
    run=client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':tid}).json()['run_id']
    help=client.post(f'/api/sessions/{sid}/hints',json={'run_id':run}).json()
    client.post(f'/api/sessions/{sid}/assistance/{help["id"]}/ack')
    client.post(f'/api/sessions/{sid}/attempts',json={'run_id':run,'response':'B','request_id':'assisted-remedy-001'})
    step=client.get(f'/api/sessions/{sid}/next').json()
    assert step['kind']=='review' and step['task_id']=='math-reference-r'


def test_archived_source_has_explicit_state_without_restoring_text(client):
    sid=client.post('/api/sessions',json={'title':'来源核查','goal':'核查证据','domain':'阅读'}).json()['id']
    mid=client.post('/api/materials',json={'title':'自备原文','text':'第一段。\n\n第二段。','session_id':sid}).json()['id']
    client.delete('/api/materials/'+mid)
    response=client.get('/api/knowledge/entry',params={'key':'material:'+mid,'session_id':sid})
    assert response.status_code==200 and response.json()['status']=='archived'
    assert response.json()['text']==''


def test_pbl_report_is_saved_facts_without_quality_score(client):
    study=client.post('/api/pbl/studies',json={'request_id':'report-start-001'}).json()
    report=client.get('/api/pbl/studies/'+study['id']+'/report').json()
    assert report['committed_steps']==0 and report['runs']['total']==0 and report['artifacts']==[]
    assert 'mastery' not in json.dumps(report)
