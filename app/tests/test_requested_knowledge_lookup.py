from fastapi.testclient import TestClient
from backend.main import app
from backend import agent

def test_explicit_knowledge_search_reads_actual_scoped_notes_and_cites_them(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'search.sqlite3'))
    with TestClient(app) as c:
        sid=c.post('/api/sessions',json={'title':'当前目标','goal':'核对资料'}).json()['id']
        other=c.post('/api/sessions',json={'title':'另一目标','goal':'另一份资料'}).json()['id']
        note=c.post('/api/notes',json={'title':'海棠笔记','text':'海棠编号 HT-7426','session_id':sid}).json()['id']
        c.post('/api/notes',json={'title':'海棠私有笔记','text':'不可跨空间读取 SECRET-OTHER-823','session_id':other})
        def model(messages,*args,**kwargs):
            context=messages[0]['content'];assert 'HT-7426' in context and 'SECRET-OTHER-823' not in context
            return {'content':'海棠笔记记录了 HT-7426。'},{'model':'test-fixture','usage':{'total_tokens':10}}
        monkeypatch.setattr(agent,'call_model',model)
        r=c.post(f'/api/sessions/{sid}/chat',json={'message':'请检索知识空间中的海棠笔记，核对编号。','request_id':'lookup-receipt-001'})
        assert r.status_code==200
        assert any(t['name']=='search_knowledge' and t['ok'] for t in r.json()['tools'])
        assert any(s['key']=='note:'+note for s in r.json()['sources'])

def test_explicit_no_search_is_respected():
    assert not agent.requests_knowledge_lookup('不要检索历史，只解释百分比。')
    assert not agent.requests_knowledge_lookup('我想知道一个概念的含义。')
    assert agent.requests_knowledge_lookup('帮我找到之前的学习记录。')
