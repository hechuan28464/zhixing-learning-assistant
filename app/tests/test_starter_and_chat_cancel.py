from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import agent,store

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'records.sqlite3'))
    with TestClient(app) as c:yield c

def test_starters_have_real_goals_and_sources_without_fabricated_attempts(client):
    from backend.starter import ensure_starters
    assert ensure_starters()['created']
    assert not ensure_starters()['created']
    data=client.get('/api/bootstrap').json()
    assert len(data['sessions'])==3 and len(data['materials'])==3
    assert all(not s['completed'] for s in data['sessions'])
    with store.db() as con:
        assert con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==0
        assert con.execute('SELECT COUNT(*) FROM messages').fetchone()[0]==0

def test_cancelled_late_reply_is_not_saved_and_next_turn_can_run(client,monkeypatch):
    sid=client.post('/api/sessions',json={'course_id':'programming'}).json()['id']
    started,release=Event(),Event();calls=[]
    def model(*args,**kwargs):
        calls.append(1)
        if len(calls)==1:
            started.set();assert release.wait(5)
            return {'content':'迟到结果不应保存'},{'model':'fixture','usage':{'total_tokens':1}}
        return {'content':'新的问题已回答'},{'model':'fixture','usage':{'total_tokens':1}}
    monkeypatch.setattr(agent,'call_model',model)
    with ThreadPoolExecutor(2) as pool:
        old=pool.submit(client.post,f'/api/sessions/{sid}/chat',json={'message':'请解释这个概念','request_id':'cancel-old-turn-001'})
        try:
            assert started.wait(3)
            stopped=client.post(f'/api/sessions/{sid}/chat/cancel',json={'request_id':'cancel-old-turn-001'})
            assert stopped.status_code==200 and stopped.json()['stopped']
            new=client.post(f'/api/sessions/{sid}/chat',json={'message':'换一个问题','request_id':'new-turn-after-stop-001'})
            assert new.status_code==200,new.text
        finally:release.set()
        assert old.result().status_code==409
    messages=client.get('/api/sessions/'+sid).json()['messages']
    assert [x['content'] for x in messages if x['role']=='assistant']==['新的问题已回答']
    with store.db() as con:assert con.execute("SELECT status FROM turns WHERE request_id='cancel-old-turn-001'").fetchone()[0]=='cancelled'
