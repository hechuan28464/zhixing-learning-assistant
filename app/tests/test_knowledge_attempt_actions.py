import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import store

@pytest.mark.parametrize('legacy',[False,True])
def test_saved_attempt_does_not_break_materials_library_or_citations(tmp_path,monkeypatch,legacy):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'knowledge.sqlite3'))
    with TestClient(app) as client:
        sid=client.post('/api/sessions',json={'course_id':'mathematics'}).json()['id']
        run=client.post(f'/api/sessions/{sid}/tasks/open',json={'task_id':'math-reference-r'}).json()['run_id']
        result=client.post(f'/api/sessions/{sid}/attempts',json={'run_id':run,'response':'A','request_id':'knowledge-contract-001'}).json()
        assert isinstance(result['next_step'],dict)
        if legacy:
            with store.db() as con:
                row=con.execute('SELECT id,result FROM attempts WHERE session_id=?',(sid,)).fetchone()
                saved=store.decode(row['result']);saved['next_step']='旧版下一步说明'
                con.execute('UPDATE attempts SET result=? WHERE id=?',(store.encode(saved),row['id']))
        mid=client.post('/api/materials',json={'title':'引用卡','text':'独立保存的原文。','session_id':sid}).json()['id']
        library=client.get('/api/knowledge',params={'session_id':sid})
        assert library.status_code==200
        material=client.get('/api/knowledge/entry',params={'key':'material:'+mid,'session_id':sid})
        assert material.status_code==200 and material.json()['paragraphs'][0]['text']=='独立保存的原文。'
        key=next(x['key'] for x in library.json()['items'] if x['kind']=='record')
        entry=client.get('/api/knowledge/entry',params={'key':key,'session_id':sid}).json()
        assert "{'kind':" not in entry['text']
        assert ('旧版下一步说明' if legacy else result['next_step']['text']) in entry['text']
