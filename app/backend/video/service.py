import hashlib,json,os,importlib.util,shutil
from pathlib import Path
from datetime import datetime,timedelta,timezone
from .. import auth
from ..store import db,decode,encode,now,new_id
from ..service import NotFound,Conflict,require_session
from . import storage,subtitles

MAX_UPLOAD=128*1024*1024
MAX_DURATION=1800

def principal():return auth.REQUEST_USER.get() or ('local' if not auth.required() else None)
def owned():
    value=principal()
    if not value:raise NotFound('请先登录，再读取自己的视频资料。')
    return value

def runtime():
    return {'ffmpeg':bool(shutil.which('ffmpeg')),'ffprobe':bool(shutil.which('ffprobe')),'downloader':bool(importlib.util.find_spec('yt_dlp')),
            'asr':bool(importlib.util.find_spec('faster_whisper')),'asr_model':os.getenv('STUDY_VIDEO_ASR_MODEL','tiny'),
            'max_upload_bytes':MAX_UPLOAD,'max_duration_seconds':MAX_DURATION,'concurrency':1,'daily_job_limit':20}

def list_assets(query='',status='',archived=False,page=1):
    owner=owned()
    with db() as c:
        records=[dict(row) for row in c.execute('SELECT * FROM video_assets WHERE owner=? AND archived=? ORDER BY updated_at DESC,id DESC',(owner,int(archived)))]
        items=[];needle=query.strip().lower()
        for row in records:
            if status=='running' and row['status'] not in ('queued','running'):continue
            if status=='completed' and row['status'] not in ('ready','completed','partial'):continue
            if status=='failed' and row['status'] not in ('failed','unknown','cancelled','partial','metadata_ready'):continue
            if needle:
                texts=[row['title'],row['author']]
                texts.extend(s['text'] for s in storage.rows(c,row['id'],row['subtitle_version']))
                texts.extend(r['data'] for r in c.execute('SELECT data FROM video_generations WHERE video_id=?',(row['id'],)))
                if needle not in '\n'.join(texts).lower():continue
            items.append(storage.public_asset(row))
    return {'items':items[(page-1)*10:page*10],'total':len(items),'page':page,'page_size':10}

def detail(identifier):
    with db() as c:
        row=storage.require(c,identifier,owned());result=storage.public_asset(row)
        result['segment_count']=c.execute('SELECT count(*) FROM video_segments WHERE video_id=? AND version=?',(identifier,row['subtitle_version'])).fetchone()[0]
        result['generations']=[{**dict(r),'data':decode(r['data']),'usage':decode(r['usage'])} for r in c.execute('SELECT * FROM video_generations WHERE video_id=? ORDER BY revision DESC',(identifier,))]
        result['frames']=[{k:v for k,v in dict(r).items() if k!='file'}|{'segment_ids':decode(r['segment_ids']),'url':f'/api/videos/{identifier}/files/'+r['file']} for r in c.execute('SELECT * FROM video_frames WHERE video_id=? ORDER BY time',(identifier,))]
        result['jobs']=[{k:v for k,v in dict(r).items() if k not in ('owner','payload','request_id')} for r in c.execute('SELECT * FROM video_jobs WHERE video_id=? ORDER BY created_at DESC,id DESC',(identifier,))]
        result['job']=result['jobs'][0] if result['jobs'] else None
        if row['platform']=='html5' and not result['media_url']:
            from .html5 import allowed
            meta=storage.folder(identifier)/'metadata.json'
            if meta.is_file():
                candidate=decode(meta.read_text(encoding='utf-8'),{}).get('html5_media_url','')
                if allowed(candidate):result['media_url']=candidate
        result['notes']=[dict(r) for r in c.execute('SELECT id,title,text,session_id,created_at,updated_at FROM video_notes WHERE video_id=? AND owner=? AND archived=0 ORDER BY updated_at DESC',(identifier,owned()))]
    return result

def segments(identifier,page=1,query='',ids=None):
    with db() as c:
        row=storage.require(c,identifier,owned());items=storage.rows(c,identifier,row['subtitle_version'])
    if ids is not None:
        keys=set(ids.split(','))
        if len(keys)>50:raise ValueError('每次最多定位50个字幕片段。')
        items=[r for r in items if r['id'] in keys]
        return {'items':items,'total':len(items),'version':row['subtitle_version']}
    if query:items=[r for r in items if query.lower() in r['text'].lower()]
    return {'items':items[(page-1)*10:page*10],'total':len(items),'page':page,'version':row['subtitle_version']}

def _job(c,video_id,kind,payload,request_id,owner):
    if not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    previous=c.execute('SELECT * FROM video_jobs WHERE owner=? AND request_id=?',(owner,request_id)).fetchone()
    if previous:
        if previous['video_id']!=video_id or previous['kind']!=kind or decode(previous['payload'])!=payload:raise Conflict('相同请求已经用于另一项视频操作。')
        return previous['id']
    if c.execute("SELECT 1 FROM video_jobs WHERE video_id=? AND state IN ('queued','running')",(video_id,)).fetchone():raise Conflict('这个视频已有处理任务，请先等待或停止。')
    day=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    if c.execute('SELECT count(*) FROM video_jobs WHERE owner=? AND date(created_at,\'+8 hours\')=?',(owner,day)).fetchone()[0]>=20:raise Conflict('今天的视频处理次数已达20次，已有资料仍可阅读。')
    identifier=new_id('vjob');stamp=now()
    c.execute('INSERT INTO video_jobs(id,video_id,owner,kind,state,stage,request_id,payload,message,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
              (identifier,video_id,owner,kind,'queued',kind,request_id,encode(payload),'任务已排队。',stamp,stamp))
    c.execute("UPDATE video_assets SET status='queued',updated_at=? WHERE id=?",(stamp,video_id))
    return identifier

def enqueue(identifier,kind,request_id,payload=None):
    owner=owned()
    with db() as c:
        row=storage.require(c,identifier,owner)
        if row['archived']:raise Conflict('请先恢复视频资料，再继续处理。')
        if kind=='generate' and not row['subtitle_version']:raise Conflict('先取得字幕，再生成总结。')
        _job(c,identifier,kind,payload or {},request_id,owner)
    from .worker import ensure_running
    ensure_running()
    return detail(identifier)

def create(url,request_id,session_id=None):
    from .media import normalize_url
    canonical,platform=normalize_url(url);owner=owned()
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        previous=c.execute('SELECT video_id FROM video_jobs WHERE owner=? AND request_id=?',(owner,request_id)).fetchone()
        if previous:
            row=storage.require(c,previous['video_id'],owner)
            if row['source_url']!=canonical or row['session_id']!=session_id:raise Conflict('相同请求对应了不同的视频链接。')
            return detail(row['id'])
        if session_id:require_session(c,session_id)
        identifier=new_id('vid');stamp=now()
        c.execute('INSERT INTO video_assets(id,owner,title,source_url,platform,status,session_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(identifier,owner,'正在读取视频信息',canonical,platform,'metadata_ready',session_id,stamp,stamp))
        _job(c,identifier,'probe',{},request_id,owner)
    from .worker import ensure_running
    ensure_running()
    return detail(identifier)

def import_subtitle(title,text,source_url,session_id,request_id):
    owner=owned();items=subtitles.parse(text)
    if items[-1]['end']>MAX_DURATION:raise ValueError('字幕超过30分钟，请按章节导入。')
    if source_url:
        from .media import normalize_url
        source_url,_=normalize_url(source_url)
    digest=hashlib.sha256((owner+'|'+request_id).encode()).hexdigest()[:24];identifier='vid_'+digest
    with db() as c:
        old=c.execute('SELECT * FROM video_assets WHERE id=? AND owner=?',(identifier,owner)).fetchone()
        if old:
            existing=storage.rows(c,identifier,1)
            if old['title']!=title or old['source_url']!=source_url or old['session_id']!=session_id or [{'start':s['start'],'end':s['end'],'text':s['text']} for s in existing]!=items:raise Conflict('相同字幕导入请求对应了不同内容。')
            return detail(identifier)
        if session_id:require_session(c,session_id)
        stamp=now()
        c.execute('INSERT INTO video_assets(id,owner,title,source_url,platform,status,session_id,duration,transcript_kind,subtitle_version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(identifier,owner,title,source_url,'subtitle','ready',session_id,items[-1]['end'],'import',1,stamp,stamp))
        _write_segments(c,identifier,1,items)
    return detail(identifier)

def _write_segments(c,identifier,version,items):
    for row in subtitles.identify(identifier,version,items):c.execute('INSERT INTO video_segments VALUES(?,?,?,?,?,?,?)',(row['id'],identifier,version,row['ordinal'],row['start'],row['end'],row['text']))

def rebind_frames(c,identifier,version):
    current_segments=storage.rows(c,identifier,version)
    current_frames=[dict(row) for row in c.execute('SELECT id,time FROM video_frames WHERE video_id=? ORDER BY time',(identifier,))]
    for index,frame in enumerate(current_frames):
        end=current_frames[index+1]['time'] if index+1<len(current_frames) else float('inf')
        related=[segment['id'] for segment in current_segments if frame['time']<=segment['start']<end]
        c.execute('UPDATE video_frames SET segment_ids=? WHERE id=?',(encode(related),frame['id']))


def replace_subtitles(identifier,text,request_id):
    owner=owned();items=subtitles.parse(text);digest=hashlib.sha256(encode(items).encode()).hexdigest()
    with db() as c:
        c.execute('BEGIN IMMEDIATE');video=storage.require(c,identifier,owner)
        previous=c.execute('SELECT * FROM video_import_requests WHERE owner=? AND request_id=?',(owner,request_id)).fetchone()
        if previous:
            if previous['video_id']!=identifier or previous['sha256']!=digest:raise Conflict('相同字幕保存请求对应了不同内容。')
            return detail(identifier)
        if c.execute("SELECT 1 FROM video_jobs WHERE video_id=? AND state IN ('queued','running')",(identifier,)).fetchone():raise Conflict('请先停止正在处理的任务，再导入字幕版本。')
        if items[-1]['end']>service_duration(video)+10:raise ValueError('字幕时间超出当前视频，请检查是否对应同一个视频。')
        version=video['subtitle_version']+1;_write_segments(c,identifier,version,items)
        rebind_frames(c,identifier,version)
        c.execute("UPDATE video_assets SET subtitle_version=?,transcript_kind='import',status='ready',updated_at=? WHERE id=?",(version,now(),identifier))
        c.execute('INSERT INTO video_import_requests VALUES(?,?,?,?,?)',(owner,request_id,identifier,digest,version))
    return detail(identifier)

def service_duration(video):return video['duration'] or MAX_DURATION

def cancel(identifier):
    with db() as c:
        storage.require(c,identifier,owned())
        if not c.execute("SELECT 1 FROM video_jobs WHERE video_id=? AND state IN ('queued','running')",(identifier,)).fetchone():return detail(identifier)
        c.execute("UPDATE video_jobs SET state='cancelled',message='已停止处理，已完成资料仍然保留。',updated_at=? WHERE video_id=? AND state IN ('queued','running')",(now(),identifier))
        c.execute("UPDATE video_assets SET status='cancelled',updated_at=? WHERE id=?",(now(),identifier))
    return detail(identifier)

def link(identifier,session_id):
    with db() as c:
        storage.require(c,identifier,owned())
        if session_id:require_session(c,session_id)
        c.execute('UPDATE video_assets SET session_id=?,updated_at=? WHERE id=?',(session_id,now(),identifier))
        c.execute('UPDATE video_notes SET session_id=? WHERE video_id=?',(session_id,identifier))
    return detail(identifier)

def archive(identifier,archived):
    with db() as c:
        storage.require(c,identifier,owned())
        if c.execute("SELECT 1 FROM video_jobs WHERE video_id=? AND state IN ('queued','running')",(identifier,)).fetchone():raise Conflict('请先停止正在处理的任务，再归档。')
        c.execute('UPDATE video_assets SET archived=?,updated_at=? WHERE id=?',(int(archived),now(),identifier))
    return {'archived':archived}

def citation(identifier,segment_ids,generation_id,published,kind,request_id):
    owner=owned()
    with db() as c:
        video=storage.require(c,identifier,owner)
        items=storage.rows(c,identifier,video['subtitle_version'])
        if segment_ids:
            wanted=set(segment_ids);items=[s for s in items if s['id'] in wanted]
            if len(items)!=len(wanted):raise NotFound('所选字幕不属于当前来源版本，请重新选择。')
        if not items:raise Conflict('字幕尚未取得，不能保存空引用。')
        generation=None
        if generation_id:
            generation=c.execute('SELECT * FROM video_generations WHERE id=? AND video_id=?',(generation_id,identifier)).fetchone()
            if not generation:raise NotFound('这份整理版本不存在。')
            if generation['source_version']!=video['subtitle_version']:raise Conflict('请先切换到匹配当前字幕的整理版本。')
        identity=encode(['citation-v2',identifier,video['subtitle_version'],[s['id'] for s in items],generation_id])
        cid='vcit_'+hashlib.sha256(identity.encode()).hexdigest()[:30]
        label=video['title']+((' · '+subtitles.timestamp(items[0]['start'])[:8]+'—'+subtitles.timestamp(items[-1]['end'])[:8]) if segment_ids else ' · 视频资料')
        origin={'course_subtitle':'公开课程SRT字幕，按官方字幕文件解析','asr':'本地语音转写，尚未校对','platform_auto':'平台自动字幕','platform_human':'平台人工字幕','html5_track':'公开网页WebVTT字幕，按原轨道解析','import':'用户导入字幕'}.get(video['transcript_kind'],'字幕来源待核对')
        parts=['视频：'+video['title'],'来源：'+(video['source_url'] or '用户上传／导入'),'文本来源：'+origin]
        if generation:
            generated=decode(generation['data']);parts+=['AI整理（请结合原句核查）：'+generated.get('summary','')]+[s['title']+'\n'+s['body'] for s in generated.get('sections',[])]
        parts+=[('语音转写 ' if video['transcript_kind']=='asr' else '原字幕 ')+subtitles.timestamp(s['start'])[:8]+'—'+subtitles.timestamp(s['end'])[:8]+'\n'+s['text'] for s in items]
        text='\n\n'.join(parts)
        c.execute('INSERT INTO video_citations(id,video_id,owner,source_version,segment_ids,generation_id,title,text,published,created_at,source_kind) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET published=max(published,excluded.published)',(cid,identifier,owner,video['subtitle_version'],encode([s['id'] for s in items]),generation_id,label,text,int(published),now(),video['transcript_kind']))
        if kind=='note':
            nid='video_note_'+hashlib.sha256(cid.encode()).hexdigest()[:24];stamp=now()
            c.execute('INSERT INTO video_notes VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(owner,citation_id) DO UPDATE SET archived=0',(nid,identifier,owner,cid,label,text,video['session_id'],0,stamp,stamp))
    return read_citation(cid)

def _entry(row,video):
    ids=decode(row['segment_ids']);source=video['author'] or video['source_url'] or '用户提供的视频资料'
    return {'key':'video:'+row['id'],'kind':'material','type_label':'视频资料','title':row['title'],'text':row['text'],'source':source,
            'updated_at':row['created_at'],'session_id':video['session_id'],'space_title':'视频研学','evidence_kind':'external_record',
            'evidence_label':('本地语音转写 · 未校对' if row['source_kind']=='asr' else '用户导入字幕' if row['source_kind']=='import' else '公开课程原字幕' if row['source_kind']=='course_subtitle' else '公开WebVTT原字幕' if row['source_kind']=='html5_track' else '视频字幕来源')+' · 不是学习效果证据','video_id':video['id'],'segment_ids':ids,'source_version':row['source_version'],
            'source_url':video['source_url'],'generation_id':row['generation_id'],'published':bool(row['published'])}

def read_citation(identifier,session_id=None):
    with db() as c:
        row=c.execute('SELECT * FROM video_citations WHERE id=? AND owner=?',(identifier,owned())).fetchone()
        if not row:raise NotFound('视频引用不存在，或不属于当前账号。')
        video=storage.require(c,row['video_id'],owned())
        if session_id and video['session_id'] not in (None,session_id):raise NotFound('这段视频未关联当前学习目标。')
        return _entry(row,video)

def knowledge_entries(con,session_id=None):
    owner=principal()
    if not owner:return []
    result=[]
    for row in con.execute('SELECT * FROM video_citations WHERE owner=? AND published=1',(owner,)):
        video=storage.require(con,row['video_id'],owner)
        if not session_id or video['session_id'] in (None,session_id):result.append(_entry(row,video))
    return result

def note_entries(con,archived=False):
    owner=principal()
    if not owner:return []
    return [dict(row) for row in con.execute('SELECT id,session_id,title,text,created_at,updated_at FROM video_notes WHERE owner=? AND archived=? ORDER BY updated_at DESC',(owner,int(archived)))]

def edit_note(identifier,title=None,text=None,archived=None):
    with db() as c:
        row=c.execute('SELECT * FROM video_notes WHERE id=? AND owner=?',(identifier,owned())).fetchone()
        if not row:raise NotFound('视频摘录不存在。')
        if title is not None:c.execute('UPDATE video_notes SET title=?,text=?,updated_at=? WHERE id=?',(title,text,now(),identifier))
        if archived is not None:c.execute('UPDATE video_notes SET archived=?,updated_at=? WHERE id=?',(int(archived),now(),identifier))
    return {'id':identifier,'archived':archived}
