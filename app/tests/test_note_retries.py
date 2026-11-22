import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'notes.sqlite3'))
    with TestClient(app) as client:yield client

def test_note_retry_reuses_same_record_and_event(client):
    payload={'title':'保存重试','text':'原始内容\n  保留换行。','request_id':'retry-note-0001'}
    first=client.post('/api/notes',json=payload)
    second=client.post('/api/notes',json=payload)
    assert first.status_code==second.status_code==200
    assert first.json()['id']==second.json()['id'] and second.json()['reused'] is True
    saved=client.get('/api/bootstrap').json()
    assert len(saved['notes'])==1 and len(saved['events'])==1
    assert saved['notes'][0]['text']==payload['text']

def test_note_request_key_cannot_change_payload(client):
    payload={'title':'保存重试','text':'最初内容','request_id':'retry-note-0002'}
    assert client.post('/api/notes',json=payload).status_code==200
    assert client.post('/api/notes',json={**payload,'text':'另一个内容'}).status_code==409
    assert client.get('/api/bootstrap').json()['notes'][0]['text']=='最初内容'

def test_invalid_note_does_not_consume_request_key(client):
    payload={'title':'   ','text':'正文','request_id':'retry-note-0003'}
    assert client.post('/api/notes',json=payload).status_code==422
    assert client.post('/api/notes',json={**payload,'title':'有效标题'}).status_code==200
    assert len(client.get('/api/bootstrap').json()['notes'])==1
