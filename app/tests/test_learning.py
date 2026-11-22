import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend import agent


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH', str(tmp_path/'learning.sqlite3'))
    with TestClient(app) as client:
        yield client


def space(client,course='mathematics'):
    response=client.post('/api/sessions',json={'course_id':course})
    assert response.status_code==200,response.text
    return response.json()


def run(client,sid,task='math-reference-r'):
    response=client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':task})
    assert response.status_code==200,response.text
    return response.json()['run_id']


def submit(client,sid,rid,response='A',key='request_000001'):
    return client.post(f'/api/sessions/{sid}/attempts',json={'run_id':rid,'response':response,'request_id':key})


def test_new_user_has_no_fabricated_learning_records(client):
    data=client.get('/api/bootstrap').json()
    assert len(data['courses'])==3
    assert data['sessions']==[] and data['events']==[]


def test_public_lesson_does_not_expose_private_answers(client):
    data=space(client)
    for lesson in data['lessons']:
        for kind in ('practice','review'):
            assert 'answer' not in lesson[kind]
            assert 'explanation' not in lesson[kind]
            assert 'hint' not in lesson[kind]


def test_review_independence_and_duplicate_submission(client):
    sid=space(client)['id'];rid=run(client,sid)
    first=submit(client,sid,rid)
    assert first.status_code==200
    assert first.json()['independent'] is True
    second=submit(client,sid,rid)
    assert second.json()['attempt_id']==first.json()['attempt_id'] and second.json()['reused'] is True
    assert len(client.get('/api/sessions/'+sid).json()['attempts'])==1
    assert submit(client,sid,rid,response='B').status_code==409


def test_undelivered_help_still_blocks_independence(client):
    sid=space(client)['id'];rid=run(client,sid)
    hint=client.post(f'/api/sessions/{sid}/hints',json={'run_id':rid}).json()
    assert hint['delivery']=='offered'
    result=submit(client,sid,rid).json()
    assert result['assistance']=='uncertain'
    assert result['correct'] is True and result['independent'] is False


def test_acknowledged_hint_is_assisted_completion(client):
    sid=space(client)['id'];rid=run(client,sid)
    hint=client.post(f'/api/sessions/{sid}/hints',json={'run_id':rid}).json()
    assert client.post(f"/api/sessions/{sid}/assistance/{hint['id']}/ack").status_code==200
    result=submit(client,sid,rid).json()
    assert result['assistance']=='delivered' and result['label']=='受助完成'


def test_repeated_exposed_question_is_not_new_independent_evidence(client):
    sid=space(client)['id'];rid=run(client,sid)
    submit(client,sid,rid,response='B')
    next_run=run(client,sid)
    assert next_run!=rid
    result=submit(client,sid,next_run,key='request_000002').json()
    assert result['correct'] is True and result['independent'] is False


def test_task_and_run_scope_checked(client):
    sid=space(client)['id'];other=space(client,'programming')['id'];rid=run(client,sid)
    assert submit(client,other,rid).status_code==404
    assert client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':'python-variable-p'}).status_code==404


def test_client_cannot_override_answer_key(client):
    sid=space(client)['id'];rid=run(client,sid)
    assert client.post(f'/api/sessions/{sid}/attempts',json={'run_id':rid,'response':'B','request_id':'request_000001','answer':'B'}).status_code==422
    assert submit(client,sid,rid,response='B').json()['correct'] is False


def test_open_answer_stays_pending(client):
    sid=space(client,'reading')['id'];rid=run(client,sid,'reading-fact-p')
    result=submit(client,sid,rid,response='新增座位是可核查陈述，最好需要明确标准与比较。').json()
    assert result['status']=='pending_review' and result['correct'] is None and not result['independent']
    states=client.get('/api/sessions/'+sid).json()['states']
    assert states['reading-fact']['status']=='pending_review'


def test_material_search_scope_and_archive(client):
    sid=space(client)['id'];other=space(client,'programming')['id']
    material=client.post('/api/materials',json={'title':'基准量笔记','text':'每个百分比都要明确基准量。','session_id':sid}).json()
    assert agent.execute_tool(sid,'search_materials',{'query':'百分比的基准量'})['results']
    assert agent.execute_tool(other,'search_materials',{'query':'基准量'})['results']==[]
    client.delete('/api/materials/'+material['id'])
    assert material['id'] not in [r['material_id'] for r in agent.execute_tool(sid,'search_materials',{'query':'基准量'})['results']]


def test_custom_subject_and_plan_revision(client,monkeypatch):
    sid=client.post('/api/sessions',json={'goal':'理解音乐节奏与诗歌韵律的联系','domain':'音乐与文学'}).json()['id']
    monkeypatch.setattr(agent,'call_model',lambda *a,**kw:({'content':json.dumps({'nodes':[{'title':'节奏与重音','objective':'区分两个具体例子','minutes':15}]})},{'model':'test'}))
    draft=client.post(f'/api/sessions/{sid}/plan').json()
    revision=draft['draft']['revision']
    assert client.post(f'/api/sessions/{sid}/plan/confirm',json={'revision':'stale'}).status_code==409
    confirmed=client.post(f'/api/sessions/{sid}/plan/confirm',json={'revision':revision}).json()
    assert confirmed['active']['revision']==revision and confirmed['draft'] is None
    regenerated=client.post(f'/api/sessions/{sid}/plan').json()
    assert regenerated['active']['revision']==revision


def test_tutor_tools_and_retry_idempotency(client,monkeypatch):
    sid=space(client)['id'];count=[]
    def fake_model(messages,tools=None,max_tokens=1400):
        count.append(1)
        if len(count)==1:return ({'content':None,'tool_calls':[{'id':'call_1','type':'function','function':{'name':'read_lesson','arguments':'{}'}}]},{'model':'test','usage':{},'seconds':0})
        assert messages[-1]['role']=='tool'
        assert '每个百分比' in messages[-1]['content']
        return ({'content':'每次变化都要先确认相对于哪个基准量。'},{'model':'test','usage':{},'seconds':0})
    monkeypatch.setattr(agent,'call_model',fake_model)
    request={'message':'请读取讲义解释基准量。','request_id':'chat_request_001'}
    first=client.post(f'/api/sessions/{sid}/chat',json=request)
    assert first.status_code==200,first.text
    assert len(first.json()['tools'])==2 and first.json()['sources']
    assert client.post(f'/api/sessions/{sid}/chat',json=request).json()==first.json()
    assert len(count)==2
    assert len(client.get('/api/sessions/'+sid).json()['messages'])==2


def test_provider_failure_preserves_question_without_fake_reply(client,monkeypatch):
    sid=space(client)['id']
    monkeypatch.setattr(agent,'call_model',lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('offline')))
    response=client.post(f'/api/sessions/{sid}/chat',json={'message':'这里没懂','request_id':'failed_request_001'})
    assert response.status_code==502
    messages=client.get('/api/sessions/'+sid).json()['messages']
    assert len(messages)==1 and messages[0]['role']=='user'


def test_tutor_help_remains_tracked_outside_lesson_view(client,monkeypatch):
    sid=space(client)['id'];rid=run(client,sid)
    monkeypatch.setattr(agent,'call_model',lambda *a,**kw:({'content':'先想想原价与折后价的关系。'},{'model':'test','usage':{},'seconds':0}))
    result=client.post(f'/api/sessions/{sid}/chat',json={'message':'我换到伙伴页面问这道题。','request_id':'cross_view_help_01'}).json()
    assert result['assistance_id']
    submitted=submit(client,sid,rid).json()
    assert not submitted['independent'] and submitted['assistance']=='uncertain'


def test_notes_profile_and_export_have_no_secrets(client):
    note=client.post('/api/notes',json={'title':'我的理解','text':'先检查基准量。'}).json()
    client.patch('/api/profile',json={'name':'测试学习者','daily_minutes':15,'style':'先举例'})
    data=client.get('/api/export').json()
    assert data['data']['profile']['name']=='测试学习者'
    assert len(data['data']['notes'])==1
    assert 'LLM_API_KEY' not in json.dumps(data)
    client.delete('/api/notes/'+note['id'])
    assert client.get('/api/bootstrap').json()['notes']==[]
    assert len(client.get('/api/bootstrap').json()['archived_notes'])==1
    assert client.post('/api/notes/'+note['id']+'/restore').status_code==200
    assert len(client.get('/api/bootstrap').json()['notes'])==1


def test_cross_origin_write_rejected(client):
    response=client.post('/api/sessions',json={'goal':'不应写入'},headers={'Origin':'https://untrusted.example'})
    assert response.status_code==403
    assert client.get('/api/bootstrap').json()['sessions']==[]


def test_original_text_is_preserved_and_material_can_restore(client):
    sid=space(client,'reading')['id'];rid=run(client,sid,'reading-fact-p')
    original='  原始作答第一行\n    保留缩进与末尾换行\n'
    assert submit(client,sid,rid,response=original).status_code==200
    assert client.get('/api/sessions/'+sid).json()['attempts'][0]['response']==original
    text='  原文第一段\n    引用缩进\n'
    material=client.post('/api/materials',json={'title':'原文资料','text':text}).json()
    assert client.get('/api/materials/'+material['id']).json()['text']==text
    client.delete('/api/materials/'+material['id'])
    assert client.get('/api/materials/'+material['id']).status_code==404
    assert client.post('/api/materials/'+material['id']+'/restore').status_code==200
    assert client.get('/api/materials/'+material['id']).json()['text']==text


def test_graph_without_structure_does_not_invent_knowledge_nodes(client):
    sid=client.post('/api/sessions',json={'goal':'探索音乐与文学的联系'}).json()['id']
    graph=client.get(f'/api/sessions/{sid}/graph').json()
    assert len(graph['nodes'])==1 and graph['nodes'][0]['kind']=='goal'
    assert graph['edges']==[]
    assert graph['nodes'][0]['source']['record_id']==sid


def test_graph_states_and_sources_come_from_saved_attempts(client):
    sid=space(client)['id'];rid=run(client,sid)
    result=submit(client,sid,rid).json()
    graph=client.get(f'/api/sessions/{sid}/graph').json()
    node=next(n for n in graph['nodes'] if n.get('lesson_id')=='math-reference')
    assert node['evidence_count']==1 and node['evidence'][0]['id']==result['attempt_id']
    assert node['status']=='independent'
    # New statistics units declare curriculum dependencies; old observations must
    # not manufacture a prerequisite attached to the legacy percentage unit.
    assert not any(e['relation']=='declared_prerequisite' and 'math-reference' in e['target'] for e in graph['edges'])
    assert all(e['provenance'] for e in graph['edges'])


def test_unconfirmed_plan_is_not_graph_fact(client,monkeypatch):
    sid=client.post('/api/sessions',json={'goal':'理解音乐节奏'}).json()['id']
    monkeypatch.setattr(agent,'call_model',lambda *a,**kw:({'content':json.dumps({'nodes':[{'title':'节拍','objective':'区分两个例子','minutes':15}]})},{'model':'test'}))
    plan=client.post(f'/api/sessions/{sid}/plan').json()
    graph=client.get(f'/api/sessions/{sid}/graph').json()
    assert len(graph['nodes'])==1 and graph['draft_available']
    client.post(f'/api/sessions/{sid}/plan/confirm',json={'revision':plan['draft']['revision']})
    confirmed=client.get(f'/api/sessions/{sid}/graph').json()
    assert len(confirmed['nodes'])==2
    assert confirmed['nodes'][1]['source']['record_id']==plan['draft']['revision']
    assert confirmed['nodes'][1]['evidence_count']==0
