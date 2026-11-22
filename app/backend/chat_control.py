"""Cooperative cancellation: a stopped turn cannot commit a late model reply."""
from contextvars import ContextVar
from threading import Event,Lock
import time
from . import auth,service
from .store import db,decode,now

_guard=Lock()
_controls={}
DEADLINE=ContextVar('tutor_deadline',default=None)

def start(session_id,request_id,session_lock):
    owner=auth.REQUEST_USER.get()
    with _guard:
        for key,value in list(_controls.items()):
            if time.monotonic()-value['created']>600:_controls.pop(key,None)
        entry=_controls.get(request_id)
        if entry and (entry['session_id']!=session_id or entry['owner']!=owner):
            raise service.Conflict('请求标识与当前学习空间不一致。')
        if not entry:
            entry={'session_id':session_id,'owner':owner,'cancelled':Event(),'created':time.monotonic()}
            _controls[request_id]=entry
        entry['lock']=session_lock
    check(entry)
    return entry

def check(entry):
    if entry['cancelled'].is_set():raise service.Conflict('已停止本次回答。')

def finish(request_id,entry):
    with _guard:
        if _controls.get(request_id) is entry:_controls.pop(request_id,None)

def cancel(session_id,request_id,session_locks):
    owner=auth.REQUEST_USER.get()
    with db() as con:
        service.require_session(con,session_id)
        turn=con.execute('SELECT * FROM turns WHERE request_id=?',(request_id,)).fetchone()
        if turn:
            if turn['session_id']!=session_id:raise service.NotFound('没有找到这次回答。')
            try:stored=decode(turn['input'],{})
            except (ValueError,TypeError):stored={}
            if isinstance(stored,dict) and stored.get('owner') and stored['owner']!=owner:
                raise service.NotFound('没有找到这次回答。')
            if turn['status']=='completed':return {'stopped':False,'status':'completed'}
    with _guard:
        entry=_controls.get(request_id)
        if entry and (entry['session_id']!=session_id or entry['owner']!=owner):
            raise service.NotFound('没有找到这次回答。')
        if not entry:
            if len(_controls)>=512:raise service.Conflict('请稍后再停止回答。')
            entry={'session_id':session_id,'owner':owner,'cancelled':Event(),'created':time.monotonic()}
            _controls[request_id]=entry
        entry['cancelled'].set()
        # The old worker releases its captured lock, never the next turn's lock.
        if entry.get('lock') is session_locks[session_id]:session_locks[session_id]=Lock()
    with db() as con:
        con.execute("UPDATE turns SET status='cancelled' WHERE request_id=? AND session_id=? AND status!='completed'",(request_id,session_id))
    return {'stopped':True,'status':'cancelled'}
