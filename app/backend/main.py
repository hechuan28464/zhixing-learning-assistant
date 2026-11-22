from contextlib import asynccontextmanager
import json
from pathlib import Path
import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import agent, service, knowledge, store, auth
from .packs import PACK_INFO, MISCONCEPTIONS
from .pbl import runtime
from .pbl import executions
from .content import COURSE_MAP, LESSONS, public_course, public_lesson
from .store import db, initialize, now, new_id, encode, decode, event
from .pbl.routes import router as pbl_router
from .pbl.engine import EngineUnavailable
from .video.routes import router as video_router
from .video import storage as video_storage,service as video_service


@asynccontextmanager
async def lifespan(app):
    initialize()
    if os.getenv('STUDY_SEED_STARTER_CONTENT','0')=='1':
        from .starter import ensure_starters
        ensure_starters()
    video_storage.initialize()
    with db() as con:video_pending=con.execute("SELECT 1 FROM video_jobs WHERE state IN ('queued','running') LIMIT 1").fetchone()
    if video_pending:
        from .video.worker import ensure_running
        ensure_running()
    executions.recover()
    # Interrupted calls retain their question but may be retried on the next request.
    with db() as con:con.execute("UPDATE turns SET status='failed' WHERE status='running'")
    try:yield
    finally:executions.recover()


app=FastAPI(title='知行伴学本地服务',version='0.3.0',lifespan=lifespan)
app.include_router(pbl_router)
app.include_router(auth.router)
app.include_router(video_router)

@app.exception_handler(EngineUnavailable)
def pbl_unavailable(request,exc):return JSONResponse({'detail':str(exc)},status_code=503)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
ORIGINS=['http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8765','http://127.0.0.1:5174','http://localhost:5174']
ORIGINS+=list(filter(None,(value.strip() for value in os.getenv('STUDY_ALLOWED_ORIGINS','').split(','))))
app.add_middleware(CORSMiddleware,allow_origins=ORIGINS,allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Content-Type'])


@app.middleware('http')
async def check_origin(request:Request,call_next):
    username=auth.current_user(request) if auth.required() else 'local'
    if request.url.path.startswith('/api/videos') and not username:return JSONResponse({'code':'login_required','detail':'登录后即可使用视频研学。'},status_code=401)
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and origin not in ORIGINS:return JSONResponse({'detail':'不接受来自其他网站的写入请求。'},status_code=403)
        if request.method=='POST' and auth.protected(request.url.path):
            blocked=auth.check_operation(request)
            if blocked:return JSONResponse(blocked['body'],status_code=blocked['status'])
    user_token=auth.REQUEST_USER.set(username)
    try:return await call_next(request)
    finally:auth.REQUEST_USER.reset(user_token)


@app.exception_handler(service.NotFound)
async def missing(request,exc):return JSONResponse({'detail':str(exc)},status_code=404)


@app.exception_handler(service.Conflict)
async def conflict(request,exc):return JSONResponse({'detail':str(exc),'retry':getattr(exc,'retry',None)},status_code=409)


@app.exception_handler(ValueError)
async def bad_value(request,exc):return JSONResponse({'detail':str(exc)[:300]},status_code=400)


class Strict(BaseModel):model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class SpaceInput(Strict):
    request_id:str|None=Field(default=None,min_length=8,max_length=100)
    course_id:str|None=None
    title:str=Field(default='',max_length=120)
    goal:str=Field(default='',max_length=2000)
    domain:str=Field(default='',max_length=100)
    foundation:str=Field(default='',max_length=500)
    daily_minutes:int=Field(default=30,ge=5,le=240)
class TaskInput(Strict):task_id:str
class HintInput(Strict):run_id:str
class AttemptInput(Strict):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    run_id:str
    response:str=Field(min_length=1,max_length=10000)
    request_id:str=Field(min_length=8,max_length=100)
class ChatInput(Strict):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    message:str=Field(min_length=1,max_length=6000)
    request_id:str=Field(min_length=8,max_length=100)
    run_id:str|None=None
    reference_ids:list[str]=Field(default_factory=list,max_length=3)
class ChatCancelInput(Strict):request_id:str=Field(min_length=8,max_length=100)
class TextInput(Strict):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    title:str=Field(min_length=1,max_length=150)
    text:str=Field(min_length=1,max_length=120000)
    session_id:str|None=None
    source:str=Field(default='手动录入',max_length=200)
    @field_validator('title','text')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('标题与正文不能只包含空白。')
        return value
class ProfileInput(Strict):
    name:str=Field(min_length=1,max_length=30)
    daily_minutes:int=Field(ge=5,le=240)
    style:str=Field(max_length=200)
    interests:list[str]=Field(default_factory=list,max_length=12)
    study_period:Literal['unspecified','morning','afternoon','evening']='unspecified'
    @field_validator('interests')
    @classmethod
    def validate_interests(cls,values):
        if any(not v.strip() or len(v)>30 for v in values):raise ValueError('兴趣标签需要为1至30字。')
        return list(dict.fromkeys(v.strip() for v in values))
class PlanInput(Strict):revision:str
class NoteInput(TextInput):request_id:str|None=Field(default=None,min_length=8,max_length=100)
class MaterialInput(TextInput):
    request_id:str|None=Field(default=None,min_length=8,max_length=100)
    evidence_kind:Literal['authored','official_doc','self_reported','external_record']='authored'
class MemoryAction(Strict):
    action:Literal['confirm','ignore','revoke']
    version:int=Field(ge=1)


@app.get('/api/health')
def health():
    with db() as con:
        schema=dict(con.execute('SELECT version,migrated_from,updated_at,warnings FROM schema_meta WHERE id=1').fetchone())
        schema['warnings']=decode(schema['warnings'],[])
        records={name:con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for name,table in [('sessions','sessions'),('attempts','attempts'),('notes','notes'),('pbl','pbl_studies')]}
        records['materials']=con.execute('SELECT COUNT(*) FROM materials WHERE lesson_id IS NULL').fetchone()[0]
        records['published_lessons']=con.execute('SELECT COUNT(*) FROM materials WHERE lesson_id IS NOT NULL').fetchone()[0]
    return {'ok':True,'application':'zhixing-learning-studio','version':'0.3.0','mode':'local-single-user','schema':schema,
            'model':{**agent.settings(),'connectivity':'not_checked_by_health'},'runner':runtime.status(),'records':records,
            'content':{'pack':PACK_INFO['id'],'version':PACK_INFO['version'],'status':PACK_INFO['status'],'tasks':PACK_INFO['task_count'],'objectives':PACK_INFO['objective_count'],'misconceptions':len(MISCONCEPTIONS),'warnings':PACK_INFO['warnings']}}


@app.get('/api/bootstrap')
def bootstrap():
    result={**service.bootstrap(),'model':agent.settings()}
    with db() as con:
        result['notes']+=video_service.note_entries(con)
        result['archived_notes']+=video_service.note_entries(con,True)
    return result


@app.get('/api/catalog/{course_id}')
def public_pack(course_id:str):
    course=COURSE_MAP.get(course_id)
    if not course:raise service.NotFound('示例课程不存在。')
    return {**public_course(course),'lessons':[public_lesson(l) for l in LESSONS if l['course_id']==course_id]}


@app.get('/api/knowledge')
def knowledge_library(query:str=Query(default='',max_length=300),kind:Literal['','material','note','record','conversation','memory']='',session_id:str|None=None,include_inactive:bool=False,limit:int=Query(default=100,ge=1,le=100),offset:int=Query(default=0,ge=0)):
    return knowledge.library(query,kind,session_id,include_inactive,limit,offset)


@app.get('/api/knowledge/entry')
def knowledge_entry(key:str=Query(max_length=250),session_id:str|None=None):return knowledge.read_entry(key,session_id)


@app.post('/api/knowledge/memories/{identifier}')
def memory_action(identifier:str,body:MemoryAction):return knowledge.change_memory(identifier,body.action,body.version)


@app.post('/api/sessions')
def create_session(body:SpaceInput):return service.create_session(**body.model_dump())


@app.get('/api/sessions/{session_id}')
def session(session_id:str):return service.session_detail(session_id)


@app.get('/api/sessions/{session_id}/graph')
def graph(session_id:str):return service.knowledge_graph(session_id)


@app.get('/api/sessions/{session_id}/next')
def next_action(session_id:str):
    with db() as con:return service.learning_evidence.next_action(con,service.require_session(con,session_id))


@app.get('/api/sessions/{session_id}/evidence')
def learning_evidence(session_id:str):
    with db() as con:return service.learning_evidence.evidence(con,service.require_session(con,session_id))


@app.post('/api/sessions/{session_id}/lessons/{lesson_id}')
def lesson(session_id:str,lesson_id:str):return service.select_lesson(session_id,lesson_id)


@app.post('/api/sessions/{session_id}/tasks/open')
def open_task(session_id:str,body:TaskInput):return service.open_task(session_id,body.task_id)


@app.post('/api/sessions/{session_id}/hints')
def hint(session_id:str,body:HintInput):return service.request_hint(session_id,body.run_id)


@app.post('/api/sessions/{session_id}/assistance/{identifier}/ack')
def acknowledge(session_id:str,identifier:str):return service.acknowledge_assistance(session_id,identifier)


@app.post('/api/sessions/{session_id}/attempts')
def attempt(session_id:str,body:AttemptInput):return service.submit_attempt(session_id,**body.model_dump())


@app.post('/api/sessions/{session_id}/chat')
def chat(session_id:str,body:ChatInput):
    try:return agent.tutor(session_id,**body.model_dump())
    except (service.NotFound,service.Conflict,ValueError):raise
    except Exception as exc:
        import logging
        detail=str(exc).lower()
        category='quota' if 'http 402' in detail else 'authentication' if 'http 401' in detail else 'timeout' if 'timeout' in detail or 'timed out' in detail else 'provider'
        logging.getLogger('zhixing.tutor').warning('tutor_failed request=%s category=%s type=%s',body.request_id,category,type(exc).__name__)
        message={'quota':'模型服务当前额度不足，问题已保留，请联系账号管理员后重试。','authentication':'模型服务认证未通过，问题已保留，请检查服务配置。','timeout':'模型响应超时，问题已保留，可以重试。','provider':'导师服务暂时没有完成回答。问题已保留，可以重试。'}[category]
        raise HTTPException(504 if category=='timeout' else 502,message) from None

@app.post('/api/sessions/{session_id}/chat/cancel')
def cancel_chat(session_id:str,body:ChatCancelInput):
    from . import chat_control
    return chat_control.cancel(session_id,body.request_id,agent._locks)


@app.post('/api/sessions/{session_id}/plan')
def plan(session_id:str):
    try:return agent.generate_plan(session_id)
    except service.NotFound:raise
    except Exception:raise HTTPException(502,'路线草案未生成或未通过检查，原目标和已确认路线仍保留。请重试。') from None


@app.post('/api/sessions/{session_id}/plan/confirm')
def confirm_plan(session_id:str,body:PlanInput):
    with db() as con:
        session=service.require_session(con,session_id)
        plan=session['plan'] if isinstance(session['plan'],dict) else {}
        draft=plan.get('draft')
        if not draft or draft['revision']!=body.revision:raise service.Conflict('路线版本已变化，请检查最新草案。')
        updated={'active':draft,'draft':None}
        con.execute("UPDATE sessions SET plan=?,plan_status='confirmed',updated_at=? WHERE id=?",(encode(updated),now(),session_id))
        event(con,session_id,'plan_confirmed','确认了学习路线',{'revision':body.revision})
    return updated


@app.post('/api/materials')
def material(body:MaterialInput):return service.save_material(**body.model_dump())


@app.get('/api/materials/{identifier}')
def read_material(identifier:str):
    with db() as con:row=con.execute('SELECT * FROM materials WHERE id=? AND archived=0',(identifier,)).fetchone()
    if not row:raise service.NotFound('资料不存在。')
    return dict(row)


@app.delete('/api/materials/{identifier}')
def archive_material(identifier:str):
    with db() as con:
        if con.execute('SELECT 1 FROM materials WHERE id=? AND lesson_id IS NOT NULL',(identifier,)).fetchone():raise service.Conflict('课程讲义保留用于来源核查，请归档自己的导入资料。')
        if not con.execute('SELECT 1 FROM materials WHERE id=?',(identifier,)).fetchone():raise service.NotFound('资料不存在。')
        con.execute('UPDATE materials SET archived=1 WHERE id=?',(identifier,))
    return {'ok':True,'archived':True}


@app.post('/api/notes')
def note(body:NoteInput):
    identifier=new_id('note')
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        payload=encode({k:v for k,v in body.model_dump().items() if k!='request_id'})
        if body.request_id:
            previous=con.execute('SELECT * FROM note_requests WHERE request_id=?',(body.request_id,)).fetchone()
            if previous:
                if previous['payload']!=payload:raise service.Conflict('相同保存请求对应了不同内容，请重新提交。')
                return {'id':previous['note_id'],'reused':True}
        if body.session_id:service.require_session(con,body.session_id)
        con.execute('INSERT INTO notes(id,session_id,title,text,created_at,updated_at) VALUES(?,?,?,?,?,?)',(identifier,body.session_id,body.title,body.text,now(),now()))
        if body.request_id:con.execute('INSERT INTO note_requests VALUES(?,?,?,?)',(body.request_id,payload,identifier,now()))
        event(con,body.session_id,'note_saved','保存笔记：'+body.title)
    return {'id':identifier}


@app.post('/api/materials/{identifier}/restore')
def restore_material(identifier:str):
    with db() as con:
        if con.execute('SELECT 1 FROM materials WHERE id=? AND lesson_id IS NOT NULL',(identifier,)).fetchone():raise service.Conflict('课程讲义版本由内容包管理。')
        if not con.execute('SELECT 1 FROM materials WHERE id=?',(identifier,)).fetchone():raise service.NotFound('资料不存在。')
        con.execute('UPDATE materials SET archived=0 WHERE id=?',(identifier,))
    return {'ok':True,'archived':False}


@app.post('/api/notes/{identifier}/restore')
def restore_note(identifier:str):
    if identifier.startswith('video_note_'):return video_service.edit_note(identifier,archived=False)
    with db() as con:
        if not con.execute('SELECT 1 FROM notes WHERE id=?',(identifier,)).fetchone():raise service.NotFound('笔记不存在。')
        con.execute('UPDATE notes SET archived=0 WHERE id=?',(identifier,))
    return {'ok':True,'archived':False}


@app.patch('/api/notes/{identifier}')
def edit_note(identifier:str,body:TextInput):
    if identifier.startswith('video_note_'):return video_service.edit_note(identifier,body.title,body.text)
    with db() as con:
        if not con.execute('SELECT 1 FROM notes WHERE id=? AND archived=0',(identifier,)).fetchone():raise service.NotFound('笔记不存在。')
        con.execute('UPDATE notes SET title=?,text=?,updated_at=? WHERE id=?',(body.title,body.text,now(),identifier))
    return {'id':identifier}


@app.delete('/api/notes/{identifier}')
def archive_note(identifier:str):
    if identifier.startswith('video_note_'):return video_service.edit_note(identifier,archived=True)
    with db() as con:con.execute('UPDATE notes SET archived=1 WHERE id=?',(identifier,))
    return {'ok':True,'archived':True}


@app.patch('/api/profile')
def profile(body:ProfileInput):
    with db() as con:con.execute('UPDATE settings SET payload=? WHERE id=1',(encode(body.model_dump()),))
    return body.model_dump()


@app.get('/api/export')
def export():
    data=bootstrap()
    with db() as con:data['video_sources']=video_service.knowledge_entries(con)
    data['sessions']=[service.session_detail(s['id']) for s in data['sessions']]
    with db() as con:
        data['materials']=[dict(r) for r in con.execute('SELECT * FROM materials WHERE archived=0 AND lesson_id IS NULL')]
        data['archived_materials']=[dict(r) for r in con.execute('SELECT * FROM materials WHERE archived=1 AND lesson_id IS NULL')]
        data['memories']=[dict(r) for r in con.execute('SELECT * FROM memories')]
        data['pbl']={name:[dict(r) for r in con.execute('SELECT * FROM '+table)] for name,table in [('studies','pbl_studies'),('artifact_versions','pbl_artifact_versions'),('events','pbl_events'),('messages','pbl_messages')]}
    return JSONResponse({'exported_at':now(),'format_version':1,'data':data},headers={'Content-Disposition':'attachment; filename="zhixing-learning-records.json"'})


@app.get('/api/export/markdown')
def export_markdown():
    data=bootstrap()
    lines=['# 知行伴学 · 我的学习记录','','导出时间：'+now(),'','## 学习目标','']
    for s in data['sessions']:
        lines.extend(['### '+s['title'],'',s['goal'],'','领域：'+s['domain'],''])
    lines.extend(['## 我的笔记',''])
    for n in data['notes']:lines.extend(['### '+n['title'],'',n['text'],''])
    with db() as con:
        for entry in video_service.knowledge_entries(con):lines.extend(['### '+entry['title'],'',entry['text'],''])
    lines.extend(['## 学习资料',''])
    with db() as con:
        for row in con.execute('SELECT title,source,text FROM materials WHERE archived=0 AND lesson_id IS NULL ORDER BY created_at DESC'):
            lines.extend(['### '+row['title'],'','来源：'+row['source'],'',row['text'],''])
        lines.extend(['## 已确认的学习记忆',''])
        for row in con.execute("SELECT text,quote FROM memories WHERE status='confirmed' ORDER BY updated_at DESC"):
            lines.extend(['- '+row['text'],'  原话：'+row['quote'],''])
    lines.extend(['## 项目保存产物',''])
    with db() as con:
        for row in con.execute('SELECT kind,text,revision,updated_at FROM pbl_artifact_versions ORDER BY updated_at'):
            lines.extend(['### '+('项目计划' if row['kind']=='plan' else '项目代码')+' · 第'+str(row['revision'])+'版','',row['text'],'','保存时间：'+row['updated_at'],''])
    return Response('\n'.join(lines),media_type='text/markdown',headers={'Content-Disposition':'attachment; filename="zhixing-learning-records.md"'})
