import json
import pytest
from fastapi.testclient import TestClient
from backend import store,auth,agent
from backend.main import app
from backend.video import service,storage,subtitles,worker,media,bilibili

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'video.sqlite3'))
    monkeypatch.setenv('STUDY_VIDEO_WORKER_DISABLED','1')
    with TestClient(app) as value:yield value

def add(client,index=0):
    return client.post('/api/videos/imports',json={'title':f'资料{index}','text':'1\n00:00:00,000 --> 00:00:03,000\n先确认输入。\n\n2\n00:00:03,500 --> 00:00:06,000\n再检查输出。','request_id':f'caption-{index:08}'}).json()

def test_10_11_21_record_paging_and_search(client):
    for i in range(21):assert add(client,i)['segment_count']==2
    first=client.get('/api/videos?page=1').json();last=client.get('/api/videos?page=3').json()
    assert first['total']==21 and len(first['items'])==10 and len(last['items'])==1
    assert not {v['id'] for v in first['items']} & {v['id'] for v in last['items']}
    assert client.get('/api/videos?query=输出').json()['total']==21

def test_resolve_retry_reuses_one_durable_job(client):
    payload={'url':'https://www.bilibili.com/video/BV1w7xd68EJE?vd_source=tracking','request_id':'resolve-once-0001'}
    a=client.post('/api/videos/resolve',json=payload);b=client.post('/api/videos/resolve',json=payload)
    assert a.status_code==b.status_code==202
    assert a.json()['id']==b.json()['id'] and len(b.json()['jobs'])==1
    assert client.get('/api/videos').json()['total']==1

def test_stable_citation_private_scope_archive_and_note_link(client,monkeypatch):
    monkeypatch.setenv('STUDY_REQUIRE_LOGIN','1')
    monkeypatch.setattr(auth,'current_user',lambda request:request.headers.get('x-test-user'))
    client.headers['x-test-user']='reader-a';asset=add(client);vid=asset['id']
    segment=client.get(f'/api/videos/{vid}/segments').json()['items'][0]
    payload={'segment_ids':[segment['id']],'kind':'note','published':True,'request_id':'citation-save-0001'}
    response=client.post(f'/api/videos/{vid}/citations',json=payload);assert response.status_code==200,response.text
    entry=response.json();key=entry['key'];assert entry['video_id']==vid and entry['source_version']==1 and '先确认输入' in entry['text']
    assert client.post(f'/api/videos/{vid}/citations',json=payload).json()['key']==key
    boot=client.get('/api/bootstrap').json();note=next(n for n in boot['notes'] if n['id'].startswith('video_note_'))
    assert client.get('/api/knowledge',params={'kind':'material'}).json()['total']==1
    assert client.patch('/api/notes/'+note['id'],json={'title':'自己的摘录','text':'带着来源继续想。','session_id':None}).status_code==200
    client.headers['x-test-user']='reader-b'
    assert client.get('/api/videos').json()['total']==0
    assert client.get(f'/api/videos/{vid}').status_code==404
    assert client.get('/api/knowledge/entry',params={'key':key}).status_code==404
    assert not client.get('/api/bootstrap').json()['notes']
    assert client.patch('/api/notes/'+note['id'],json={'title':'别人的摘录','text':'不应该写入'}).status_code==404
    client.headers['x-test-user']='reader-a'
    assert client.post(f'/api/videos/{vid}/archive',json={'archived':True}).status_code==200
    assert client.get('/api/videos').json()['total']==0
    assert client.get('/api/knowledge/entry',params={'key':key}).json()['text']==entry['text']
    assert client.get('/api/videos?archived=true').json()['total']==1
    client.headers.pop('x-test-user')
    assert client.get('/api/videos').status_code==401
    assert client.get(f'/api/videos/{vid}/files/metadata.json').status_code==401

def test_no_source_forgery_and_old_citation_survives_new_transcript(client):
    asset=add(client);vid=asset['id'];items=client.get(f'/api/videos/{vid}/segments').json()['items']
    bad=client.post(f'/api/videos/{vid}/citations',json={'segment_ids':['other-video-segment'],'request_id':'bad-citation-0001'})
    assert bad.status_code==404
    key=client.post(f'/api/videos/{vid}/citations',json={'segment_ids':[items[0]['id']],'request_id':'old-citation-001'}).json()['key']
    old=client.get('/api/knowledge/entry',params={'key':key}).json()['text']
    with store.db() as c:
        service._write_segments(c,vid,2,[{'start':0,'end':2,'text':'新版不同文字'}]);c.execute('UPDATE video_assets SET subtitle_version=2 WHERE id=?',(vid,))
    assert client.get('/api/knowledge/entry',params={'key':key}).json()['text']==old

def test_import_subtitles_as_new_version_preserves_original_origin_and_retry(client):
    vid=add(client)['id']
    with store.db() as c:c.execute("UPDATE video_assets SET transcript_kind='asr' WHERE id=?",(vid,))
    segment=client.get(f'/api/videos/{vid}/segments').json()['items'][0]
    key=client.post(f'/api/videos/{vid}/citations',json={'segment_ids':[segment['id']],'request_id':'asr-citation-001'}).json()['key']
    old=client.get('/api/knowledge/entry',params={'key':key}).json()
    payload={'request_id':'new-subtitle-0001','text':'1\n00:00:00,000 --> 00:00:03,000\n用户导入的校订文字'}
    for _ in range(2):
        result=client.post(f'/api/videos/{vid}/subtitles',json=payload)
        assert result.status_code==200 and result.json()['subtitle_version']==2
    preserved=client.get('/api/knowledge/entry',params={'key':key}).json()
    assert preserved['text']==old['text'] and '语音转写' in preserved['evidence_label']
    assert client.get(f'/api/videos/{vid}/segments').json()['items'][0]['text']=='用户导入的校订文字'
    assert client.post(f'/api/videos/{vid}/subtitles',json={**payload,'text':payload['text']+'不同内容'}).status_code==409

def test_queued_idempotence_cancel_and_recovery(client):
    asset=add(client);vid=asset['id'];payload={'request_id':'processing-once-001','frames':False}
    first=client.post(f'/api/videos/{vid}/process',json=payload);assert first.status_code==202
    second=client.post(f'/api/videos/{vid}/process',json=payload);assert second.status_code==202
    assert len(second.json()['jobs'])==1
    assert client.post(f'/api/videos/{vid}/process',json={**payload,'frames':True}).status_code==409
    assert client.post(f'/api/videos/{vid}/cancel').json()['job']['state']=='cancelled'
    with store.db() as c:
        c.execute("UPDATE video_jobs SET state='running'");c.execute("UPDATE video_assets SET status='running'")
    worker.recover()
    assert client.get(f'/api/videos/{vid}').json()['job']['state']=='unknown'
    assert client.get(f'/api/videos/{vid}').json()['segment_count']==2

def test_model_output_must_reference_actual_segments_and_keep_usage(client,monkeypatch):
    vid=add(client)['id'];items=client.get(f'/api/videos/{vid}/segments').json()['items'];sid=items[0]['id']
    def answer(messages,**kwargs):return {'content':json.dumps({'title':'真实字幕整理','summary':'确认输入，再检查输出。','sections':[{'title':'确认结构','body':'确认输入与输出。','segment_ids':[sid]}],'outline':{'label':'输入输出','segment_ids':[],'children':[{'label':'确认输入','segment_ids':[sid],'children':[]}]}})},{'usage':{'total_tokens':101,'prompt_tokens':80,'completion_tokens':21}}
    monkeypatch.setattr(agent,'call_model',answer)
    job=client.post(f'/api/videos/{vid}/generate',json={'request_id':'generate-test-001'}).json()['job']
    with store.db() as c:c.execute("UPDATE video_jobs SET state='running' WHERE id=?",(job['id'],));saved=dict(c.execute('SELECT * FROM video_jobs WHERE id=?',(job['id'],)).fetchone())
    worker.execute(saved)
    detail=client.get(f'/api/videos/{vid}').json();assert detail['status']=='completed'
    assert detail['generations'][0]['usage']['total_tokens']==101
    assert detail['generations'][0]['data']['sections'][0]['segment_ids']==[sid]
    assert client.get(f'/api/videos/{vid}/export?kind=md&generation_id='+detail['generations'][0]['id']).status_code==200
    updated=client.post(f'/api/videos/{vid}/subtitles',json={'request_id':'replace-after-generation','text':'1\n00:00:00,000 --> 00:00:03,000\n新字幕正文。'})
    assert updated.status_code==200
    assert client.get(f'/api/videos/{vid}/export?kind=md&generation_id='+detail['generations'][0]['id']).status_code==409

def test_timestamp_parsers_normalization_and_private_network():
    assert subtitles.parse('WEBVTT\n\n00:01.000 --> 00:02.500\n<b>真实字幕</b>')[0]=={'start':1.0,'end':2.5,'text':'真实字幕'}
    assert subtitles.parse('{"body":[{"from":1,"to":3,"content":"B站原文"}]}')[0]['text']=='B站原文'
    for text in ('没有时间戳','1\n00:00:02,000 --> 00:00:01,000\n不正确'):
        with pytest.raises(ValueError):subtitles.parse(text)
    url,_=media.normalize_url('【视频标题】https://www.bilibili.com/video/BV1w7xd68EJE?vd_source=track')
    assert url=='https://www.bilibili.com/video/BV1w7xd68EJE'
    for invalid in ('http://127.0.0.1/','https://example.org/video','https://user:pass@www.bilibili.com/video/BVx'):
        with pytest.raises(ValueError):media.normalize_url(invalid)
    with media.public_network():
        import socket
        with pytest.raises(ValueError):socket.socket().connect(('127.0.0.1',80))

def test_protobuf_captions_preserve_unknown_fields_and_bind_language():
    def field(n,text):value=text.encode() if isinstance(text,str) else text;return bytes([n*8+2,len(value)])+value
    track=field(3,'ai-zh')+field(4,'中文AI')+field(5,'//aisubtitle.hdslb.com/example.json')+b'\x48\x01'
    result=bilibili.protobuf_tracks(field(1,field(3,track)))
    assert result[0]['lan']=='ai-zh' and result[0]['subtitle_url'].startswith('//aisubtitle')
    with pytest.raises(ValueError):bilibili.protobuf_tracks(b'\x0a\xff')

def test_public_subtitles_never_require_or_read_a_cookie_file(monkeypatch):
    expected=[{'start':0,'end':2,'text':'公开字幕'}];calls=[]
    monkeypatch.setattr(bilibili,'_extract_with_cookie',lambda url,cookie:(calls.append(cookie) or expected,'platform_human',''))
    monkeypatch.setattr(bilibili,'configured_cookie',lambda:pytest.fail('Public caption path must not read credentials'))
    assert bilibili.extract('https://www.bilibili.com/video/BV1w7xd68EJE')[0]==expected
    assert calls==['']

@pytest.mark.parametrize('failure',['network','duration'])
def test_track_discovery_errors_are_not_mislabeled_as_login(monkeypatch,failure):
    def reply(path,params,cookie=''):
        if path=='x/web-interface/view':return json.dumps({'code':0,'data':{'aid':1,'cid':2,'bvid':'BV1w7xd68EJE','duration':6,'pages':[{'cid':2,'duration':6}]}}).encode()
        return json.dumps({'code':0,'data':{'need_login_subtitle':True,'subtitle':{'subtitles':[{'lan':'ai-zh','subtitle_url':'https://subtitle.bilibili.com/example'}]}}}).encode()
    monkeypatch.setattr(bilibili,'request',reply)
    monkeypatch.setattr(bilibili,'signed',lambda params,cookie:params)
    def body(*args,**kwargs):
        if failure=='network':raise OSError('unavailable')
        return b'{"body":[{"from":0,"to":100,"content":"wrong video range"}]}'
    monkeypatch.setattr(media,'fetch_bytes',body)
    items,kind,reason=bilibili._extract_with_cookie('https://www.bilibili.com/video/BV1w7xd68EJE')
    assert items is None
    assert ('正文读取未成功' in reason) if failure=='network' else ('时间范围' in reason)
    assert '接口要求有效B站登录态' not in reason

def test_authorized_fallback_runs_only_after_public_track_absence(monkeypatch):
    expected=[{'start':0,'end':2,'text':'授权字幕'}];calls=[]
    def extract(url,cookie):
        calls.append(cookie)
        return (expected,'platform_auto','') if cookie else (None,'','平台要求登录态')
    monkeypatch.setattr(bilibili,'_extract_with_cookie',extract)
    monkeypatch.setattr(bilibili,'configured_cookie',lambda:'test-only-cookie')
    assert bilibili.extract('https://www.bilibili.com/video/BV1w7xd68EJE')[0]==expected
    assert calls==['','test-only-cookie']

def test_saved_captions_can_be_reused_without_bilibili_login_or_requests(client,monkeypatch):
    asset=add(client);vid=asset['id']
    with store.db() as c:c.execute("UPDATE video_assets SET platform='bilibili',source_url='https://www.bilibili.com/video/BV1w7xd68EJE',transcript_kind='platform_auto' WHERE id=?",(vid,))
    monkeypatch.setattr(bilibili,'extract',lambda *_:pytest.fail('Saved transcript must not fetch Bilibili again'))
    monkeypatch.setattr(media,'probe',lambda *_:pytest.fail('Saved transcript must not probe Bilibili again'))
    response=client.post(f'/api/videos/{vid}/process',json={'request_id':'reuse-saved-captions-001','frames':False})
    with store.db() as c:
        c.execute("UPDATE video_jobs SET state='running' WHERE id=?",(response.json()['job']['id'],))
        job=dict(c.execute('SELECT * FROM video_jobs WHERE id=?',(response.json()['job']['id'],)).fetchone())
    worker.execute(job)
    assert client.get(f'/api/videos/{vid}').json()['segment_count']==2

def test_refresh_platform_failure_preserves_previous_text_and_does_not_start_asr(client,monkeypatch):
    vid=add(client)['id']
    with store.db() as c:c.execute("UPDATE video_assets SET platform='bilibili',source_url='https://www.bilibili.com/video/BV1w7xd68EJE' WHERE id=?",(vid,))
    monkeypatch.setattr(bilibili,'extract',lambda *_:(None,'','平台接口要求登录态'))
    monkeypatch.setattr(media,'captions',lambda *_:(None,''))
    monkeypatch.setattr(media,'probe',lambda *_:({},{}))
    monkeypatch.setattr(media,'transcribe',lambda *_:pytest.fail('Explicit platform refresh must not silently transcribe'))
    response=client.post(f'/api/videos/{vid}/process',json={'request_id':'refresh-platform-001','frames':False,'allow_asr':False,'refresh_subtitles':True})
    with store.db() as c:
        c.execute("UPDATE video_jobs SET state='running' WHERE id=?",(response.json()['job']['id'],))
        job=dict(c.execute('SELECT * FROM video_jobs WHERE id=?',(response.json()['job']['id'],)).fetchone())
    with pytest.raises(ValueError,match='登录态'):worker.execute(job)
    detail=client.get(f'/api/videos/{vid}').json()
    assert detail['subtitle_version']==1 and detail['segment_count']==2
