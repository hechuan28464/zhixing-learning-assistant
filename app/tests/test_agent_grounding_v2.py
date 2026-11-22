import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import agent,store,knowledge,auth
from backend.video import html5,subtitles,media

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'agent.sqlite3'))
    with TestClient(app) as c:yield c

def usage():return {'model':'fixture','usage':{'total_tokens':20}}

def test_selected_reference_survives_full_course_context_and_scope_is_enforced(client,monkeypatch):
    sid=client.post('/api/sessions',json={'course_id':'programming'}).json()['id']
    mid=client.post('/api/materials',json={'title':'引用原文','text':'原始片段 '+('甲'*7500)+' REF-END-7742','session_id':sid}).json()['id']
    calls=[]
    def model(messages,*args,**kwargs):
        calls.append(messages)
        assert 'REF-END-7742' in messages[0]['content']
        assert '课外秘密' not in messages[0]['content']
        if len(calls)==1:return {'tool_calls':[{'id':'outside','type':'function','function':{'name':'read_lesson','arguments':'{}'}}]},usage()
        assert json.loads(messages[-1]['content'])['ok'] is False
        return {'content':'仅依据所选引用作答。'},usage()
    monkeypatch.setattr(agent,'call_model',model)
    result=client.post(f'/api/sessions/{sid}/chat',json={'message':'请只依据当前引用解释含义。','reference_ids':['material:'+mid],'request_id':'strict-source-test-001'})
    assert result.status_code==200,result.text
    data=result.json();assert data['answer_scope']=='selected_references'
    assert {r['key'] for r in data['sources']}=={'material:'+mid}
    assert any(r['name']=='read_lesson' and not r['ok'] for r in data['tools'])

def test_next_action_uses_saved_policy_and_does_not_write_grade(client,monkeypatch):
    sid=client.post('/api/sessions',json={'course_id':'reading'}).json()['id']
    client.post(f'/api/sessions/{sid}/lessons/crit-ch01')
    before=client.get(f'/api/sessions/{sid}').json()['states']
    expected=client.get(f'/api/sessions/{sid}/next').json()
    def model(messages,*args,**kwargs):
        assert expected['task_id'] in messages[0]['content']
        return {'content':'先用本单元诊断确认起点。'},usage()
    monkeypatch.setattr(agent,'call_model',model)
    data=client.post(f'/api/sessions/{sid}/chat',json={'message':'我接下来学什么，给我下一步建议。','request_id':'policy-next-test-001'}).json()
    assert data['next_action']['task_id']==expected['task_id']
    assert data['next_action']['session_id']==sid
    assert client.get(f'/api/sessions/{sid}').json()['states']==before

def test_read_source_enforces_space_and_preserves_paragraph_locator(client):
    a=client.post('/api/sessions',json={'goal':'甲目标'}).json()['id'];b=client.post('/api/sessions',json={'goal':'乙目标'}).json()['id']
    mid=client.post('/api/materials',json={'title':'两段材料','text':'第一段\n\n第二段有关键证据。','session_id':a}).json()['id']
    result=agent.execute_tool(a,'read_source',{'key':'material:'+mid,'paragraph':2})
    assert result['text']=='第二段有关键证据。' and result['locator'].endswith('#p2')
    with pytest.raises(ValueError):agent.execute_tool(b,'read_source',{'key':'material:'+mid,'paragraph':2})

def test_public_html5_adapter_reads_real_track_structure_without_arbitrary_url(monkeypatch):
    page=b'<h1>Caption course</h1><video><source src="video/clip.mp4" type="video/mp4"><track kind="subtitles" srclang="en" src="subtitles/en.vtt"></video>'
    monkeypatch.setattr(media,'fetch_bytes',lambda *args,**kwargs:page)
    info,meta=html5.probe(html5.PREFIX)
    assert info['subtitles']['en'][0]['url']==html5.PREFIX+'subtitles/en.vtt'
    assert meta['platform']=='html5'
    with pytest.raises(ValueError):html5.probe('https://example.org/')


def test_confirmed_memory_from_another_account_is_not_given_to_tutor(client):
    sid=client.post('/api/sessions',json={'goal':'共享目标中的个人偏好'}).json()['id']
    from backend.store import db,encode,now
    with db() as con:
        for owner in ['reader-a','reader-b']:
            mid='source-'+owner
            con.execute('INSERT INTO messages VALUES(?,?,?,?,?,?)',(mid,sid,'user','我希望用'+owner+'的例子解释',encode({'owner':owner}),now()))
            item=knowledge.propose_memory(con,sid,mid,owner+'偏好','我希望用'+owner+'的例子解释')
            con.execute("UPDATE memories SET status='confirmed' WHERE id=?",(item['id'],))
    token=auth.REQUEST_USER.set('reader-a')
    try:assert [m['text'] for m in knowledge.confirmed_memories(sid)]==['reader-a偏好']
    finally:auth.REQUEST_USER.reset(token)


def test_html5_citation_keeps_original_track_provenance(client,monkeypatch):
    from backend.video import service as videos
    monkeypatch.setenv('STUDY_VIDEO_WORKER_DISABLED','1')
    video=client.post('/api/videos/imports',json={'title':'公开轨道','text':'1\n00:00:01,000 --> 00:00:03,000\nA real caption.','request_id':'webvtt-provenance-001'}).json()
    with store.db() as con:con.execute("UPDATE video_assets SET transcript_kind='html5_track' WHERE id=?",(video['id'],))
    entry=videos.citation(video['id'],[],None,True,'material','webvtt-citation-001')
    assert '公开网页WebVTT字幕，按原轨道解析' in entry['text']
    assert '公开WebVTT原字幕' in entry['evidence_label']
