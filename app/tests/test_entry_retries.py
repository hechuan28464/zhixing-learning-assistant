"""A lost response must not create duplicate goals, materials or learning events."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'entry-retries.sqlite3'))
    with TestClient(app) as client:yield client

def test_custom_goal_retry_is_one_goal_and_one_event(client):
    payload={'goal':'比较桥梁结构与承重','request_id':'entry-goal-retry-01'}
    first=client.post('/api/sessions',json=payload)
    retry=client.post('/api/sessions',json=payload)
    assert first.status_code==retry.status_code==200
    assert first.json()['id']==retry.json()['id']
    saved=client.get('/api/bootstrap').json()
    assert len(saved['sessions'])==len(saved['events'])==1

def test_goal_retry_rejects_changed_content(client):
    payload={'goal':'原来的目标','request_id':'entry-goal-retry-02'}
    assert client.post('/api/sessions',json=payload).status_code==200
    assert client.post('/api/sessions',json={**payload,'goal':'另一个目标'}).status_code==409
    assert len(client.get('/api/bootstrap').json()['sessions'])==1

def test_reused_course_binds_request_key_to_payload(client):
    original=client.post('/api/sessions',json={'course_id':'reading'}).json()
    payload={'course_id':'reading','request_id':'entry-course-retry-01'}
    assert client.post('/api/sessions',json=payload).json()['id']==original['id']
    assert client.post('/api/sessions',json={**payload,'course_id':'programming'}).status_code==409
    assert len(client.get('/api/bootstrap').json()['sessions'])==1

def test_material_retry_preserves_text_and_scope(client):
    space=client.post('/api/sessions',json={'goal':'解释观察依据'}).json()
    payload={'title':'观察记录','text':'原文\n  保留空白。','session_id':space['id'],'request_id':'entry-material-retry-01'}
    first=client.post('/api/materials',json=payload)
    retry=client.post('/api/materials',json=payload)
    assert first.status_code==retry.status_code==200
    assert first.json()['id']==retry.json()['id'] and retry.json()['reused']
    material=client.get('/api/materials/'+first.json()['id']).json()
    assert material['text']==payload['text'] and material['session_id']==space['id']
    saved=client.get('/api/bootstrap').json()
    assert len(saved['materials'])==1 and len(saved['events'])==2
    assert client.post('/api/materials',json={**payload,'text':'修改后的内容'}).status_code==409

def test_material_retry_does_not_restore_archived_material(client):
    payload={'title':'资料','text':'一份资料','request_id':'entry-material-retry-02'}
    identifier=client.post('/api/materials',json=payload).json()['id']
    assert client.delete('/api/materials/'+identifier).status_code==200
    assert client.post('/api/materials',json=payload).json()['id']==identifier
    saved=client.get('/api/bootstrap').json()
    assert not saved['materials'] and len(saved['archived_materials'])==1

def test_invalid_material_does_not_consume_request_key(client):
    payload={'title':'资料','text':' ','request_id':'entry-material-retry-03'}
    assert client.post('/api/materials',json=payload).status_code==422
    assert client.post('/api/materials',json={**payload,'text':'有效内容'}).status_code==200

def test_same_text_with_new_request_can_be_saved_intentionally(client):
    payload={'title':'资料','text':'同一原文'}
    first=client.post('/api/materials',json={**payload,'request_id':'entry-material-new-01'}).json()
    second=client.post('/api/materials',json={**payload,'request_id':'entry-material-new-02'}).json()
    assert first['id']!=second['id']
