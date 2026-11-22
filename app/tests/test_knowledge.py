import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import agent,knowledge
from backend.store import db,encode,new_id,now


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'knowledge.sqlite3'))
    with TestClient(app) as client:yield client


def goal(client,title='跨学科阅读'):
    return client.post('/api/sessions',json={'title':title,'goal':title}).json()['id']


def preference(sid):
    mid=new_id('msg')
    with db() as con:
        con.execute('INSERT INTO messages VALUES(?,?,?,?,?,?)',(mid,sid,'user','我希望先看例子，再解释概念。','{}',now()))
        knowledge.capture_preference(con,sid,mid,'我希望先看例子，再解释概念。')
    return mid


def test_empty_library_and_real_data_scope(client):
    assert client.get('/api/knowledge').json()['total']==0
    a,b=goal(client,'数学与艺术'),goal(client,'阅读与论证')
    public=client.post('/api/materials',json={'title':'公共阅读','text':'从事实寻找证据。'}).json()['id']
    private=client.post('/api/materials',json={'title':'空间独有材料','text':'矩阵对应变换','session_id':a}).json()['id']
    items=client.get('/api/knowledge',params={'session_id':b}).json()['items']
    assert {e['key'] for e in items}=={'material:'+public}
    assert client.get('/api/knowledge/entry',params={'key':'material:'+private,'session_id':b}).status_code==404
    assert client.get('/api/knowledge',params={'query':'矩阵'}).json()['total']==1
    client.delete('/api/materials/'+private)
    assert client.get('/api/knowledge',params={'query':'矩阵'}).json()['total']==0


def test_course_material_is_published_source_not_hidden_answers(client):
    s=client.post('/api/sessions',json={'course_id':'programming'}).json()
    items=client.get('/api/knowledge').json()['items']
    assert len(items)==len(s['lessons'])
    for item in items:
        entry=client.get('/api/knowledge/entry',params={'key':item['key']}).json()
        assert 'answer' not in entry and 'explanation' not in entry
        assert entry['source']=='自编示例讲义 · v1'


def test_memory_lifecycle_quote_and_version(client):
    sid=goal(client);mid=preference(sid)
    item=client.get('/api/knowledge',params={'kind':'memory'}).json()['items'][0]
    key=item['key'];identifier=key.split(':')[1]
    assert knowledge.confirmed_memories(sid)==[]
    original=client.get('/api/knowledge/entry',params={'key':'conversation:'+mid}).json()
    entry=client.get('/api/knowledge/entry',params={'key':key}).json()
    assert entry['quote'] in original['text']
    # Opening/read-only dialog preparation does not mutate status.
    assert client.get('/api/knowledge/entry',params={'key':key}).json()['status']=='pending'
    result=client.post('/api/knowledge/memories/'+identifier,json={'action':'confirm','version':1})
    assert result.status_code==200 and result.json()['status']=='confirmed'
    assert len(knowledge.confirmed_memories(sid))==1
    assert client.post('/api/knowledge/memories/'+identifier,json={'action':'ignore','version':1}).status_code==409
    assert client.post('/api/knowledge/memories/'+identifier,json={'action':'revoke','version':2}).json()['status']=='revoked'
    assert knowledge.confirmed_memories(sid)==[]
    with db() as con:knowledge.capture_preference(con,sid,mid,original['text'])
    assert client.get('/api/knowledge',params={'kind':'memory'}).json()['total']==0
    assert client.get('/api/knowledge',params={'kind':'memory','include_inactive':True}).json()['total']==1


def test_ignore_retains_source_and_never_enters_agent_context(client):
    sid=goal(client);mid=preference(sid)
    memory=client.get('/api/knowledge',params={'kind':'memory'}).json()['items'][0]
    assert agent.execute_tool(sid,'get_learning_context',{})['confirmed_memories']==[]
    assert not any(r['kind']=='memory' for r in agent.execute_tool(sid,'search_knowledge',{'query':'例子'})['results'])
    result=client.post('/api/knowledge/memories/'+memory['key'].split(':')[1],json={'action':'ignore','version':1})
    assert result.json()['status']=='ignored'
    assert client.get('/api/knowledge/entry',params={'key':'conversation:'+mid}).status_code==200
    assert client.get('/api/export').json()['data']['memories'][0]['status']=='ignored'


def test_memory_requires_exact_current_user_source(client):
    a,b=goal(client),goal(client,'另一个目标');mid=preference(a)
    with db() as con:
        with pytest.raises(ValueError):knowledge.propose_memory(con,b,mid,'用户喜欢图解','先看例子')
        with pytest.raises(ValueError):knowledge.propose_memory(con,a,mid,'用户喜欢图解','不存在的原文')


def test_discussion_citation_persists_and_rejects_foreign_scope(client,monkeypatch):
    a,b=goal(client),goal(client,'另一个目标')
    material=client.post('/api/materials',json={'title':'原始资料','text':'事实需要证据来核查。','session_id':a}).json()['id']
    captured=[]
    def model(messages,tools=None,max_tokens=1400):
        captured.extend(messages)
        return {'content':'可以检查证据与结论的联系。'},{'model':'test-model','seconds':0,'usage':{}}
    monkeypatch.setattr(agent,'call_model',model)
    body={'message':'如何理解这段话？','request_id':'citation-test-001','reference_ids':['material:'+material]}
    assert client.post('/api/sessions/'+b+'/chat',json=body).status_code==404
    response=client.post('/api/sessions/'+a+'/chat',json=body)
    assert response.status_code==200
    assert '事实需要证据来核查。' in captured[0]['content']
    messages=client.get('/api/sessions/'+a).json()['messages']
    assert messages[0]['metadata']['references'][0]['key']=='material:'+material
    assert response.json()['sources'][0]['title']=='原始资料'
    assert client.post('/api/sessions/'+a+'/chat',json=body).status_code==200
    assert len(client.get('/api/sessions/'+a).json()['messages'])==2


def test_chat_automatically_creates_pending_candidate_once(client,monkeypatch):
    sid=goal(client)
    monkeypatch.setattr(agent,'call_model',lambda *a,**k:({'content':'先看一个例子。'},{'model':'test','seconds':0,'usage':{}}))
    body={'message':'我希望先看例子，再解释概念。','request_id':'preference-test-001'}
    assert client.post('/api/sessions/'+sid+'/chat',json=body).status_code==200
    assert client.post('/api/sessions/'+sid+'/chat',json=body).status_code==200
    memory=client.get('/api/knowledge',params={'kind':'memory'}).json()
    assert memory['total']==1 and memory['items'][0]['status']=='pending'
    assert knowledge.confirmed_memories(sid)==[]
