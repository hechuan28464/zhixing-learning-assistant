import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'features.sqlite3'))
    with TestClient(app) as client:yield client


def test_catalog_preview_has_content_but_no_fake_learner_or_answer_keys(client):
    pack=client.get('/api/catalog/reading')
    assert pack.status_code==200
    assert len(pack.json()['lessons'])==10
    for lesson in pack.json()['lessons']:
        for kind in ['practice','review']:
            assert 'answer' not in lesson[kind] and 'explanation' not in lesson[kind]
    assert client.get('/api/bootstrap').json()['sessions']==[]
    assert client.get('/api/catalog/unknown').status_code==404


def test_extended_preferences_are_explicit_and_validated(client):
    preferences={'name':'学习者','style':'先举例','daily_minutes':30,'interests':['科学与生活','阅读与写作','科学与生活'],'study_period':'afternoon'}
    result=client.patch('/api/profile',json=preferences)
    assert result.status_code==200
    saved=client.get('/api/bootstrap').json()['profile']
    assert saved['interests']==['科学与生活','阅读与写作'] and saved['study_period']=='afternoon'
    assert client.patch('/api/profile',json={**preferences,'study_period':'guess'}).status_code==422
    assert client.patch('/api/profile',json={**preferences,'interests':['x'*31]}).status_code==422


def test_markdown_export_contains_only_saved_content(client):
    session=client.post('/api/sessions',json={'title':'我的实践','goal':'记录真实观察'}).json()
    client.post('/api/notes',json={'title':'项目记录｜纸桥承重实验｜观察与解释','text':'用户记录：纸桥弯曲，尚未测量重量。','session_id':session['id']})
    exported=client.get('/api/export/markdown')
    assert exported.status_code==200 and 'text/markdown' in exported.headers['content-type']
    assert '我的实践' in exported.text and '尚未测量重量' in exported.text
    assert 'LLM_API_KEY' not in exported.text and 'sk_tr_' not in exported.text


def test_project_observation_is_note_evidence_not_completed_or_mastered(client):
    session=client.post('/api/sessions',json={'title':'纸桥承重实验','goal':'探究结构与承重','domain':'跨学科实践'}).json()
    response=client.post('/api/notes',json={'title':'项目记录｜纸桥承重实验｜提出预测','text':'预测：折叠后可能承重更多。记录来源：学习者填写，尚未经独立核查。','session_id':session['id']})
    assert response.status_code==200
    entry=client.get('/api/knowledge',params={'kind':'note','session_id':session['id']}).json()['items'][0]
    assert entry['kind']=='note' and entry['session_id']==session['id']
    saved=client.get('/api/sessions/'+session['id']).json()
    assert saved['states']=={} and saved['attempts']==[]
