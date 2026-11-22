"""Durable check requests with bounded workers and host-owned result commitment."""
import threading
import time
from uuid import uuid4
from ..store import db,database_path,database_scope,decode,encode,new_id,now
from .. import service as learning
from . import runtime

_slots=threading.BoundedSemaphore(2)
_capacity=threading.BoundedSemaphore(10)


def public_job(con,row):
    item=dict(row)
    code=con.execute("SELECT sha256,revision FROM pbl_artifacts WHERE study_id=? AND kind='code'",(item['study_id'],)).fetchone()
    return {'job_id':item['id'],'study_id':item['study_id'],'state':item['state'],'source_sha256':item['source_sha256'],
            'artifact_revision':item['artifact_revision'],'expected_revision':item['expected_revision'],
            'current_version':bool(code and code['sha256']==item['source_sha256'] and code['revision']==item['artifact_revision']),
            'result':decode(item['result']),'detail':item['detail'],'started_at':item['started_at'],'updated_at':item['updated_at']}


def _require_job(con,study_id,job_id):
    from .service import require
    require(con,study_id)
    row=con.execute('SELECT * FROM executions WHERE id=? AND study_id=?',(job_id,study_id)).fetchone()
    if not row:raise learning.NotFound('检查请求不存在，或不属于当前项目。')
    return row


def read(study_id,job_id):
    with db() as con:return public_job(con,_require_job(con,study_id,job_id))


def latest(con,study_id):
    row=con.execute('SELECT * FROM executions WHERE study_id=? ORDER BY started_at DESC,rowid DESC LIMIT 1',(study_id,)).fetchone()
    return public_job(con,row) if row else None


def _uncertain(job_id,token):
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT * FROM executions WHERE id=?',(job_id,)).fetchone()
        if not row:return
        updated=con.execute("UPDATE executions SET state='unknown',detail=?,updated_at=? WHERE id=? AND state IN ('pending','running') AND (worker_token=? OR (worker_token IS NULL AND state='pending'))",
                            ('未取得可确认的完整结果，不计为代码错误；可以查询记录或重新检查。',now(),job_id,token))
        if updated.rowcount:con.execute('UPDATE pbl_studies SET busy_token=NULL,busy_until=NULL WHERE id=? AND busy_token=?',(row['study_id'],row['id']))


def _worker(path,job_id,executor):
    with database_scope(path),_slots:
        token=uuid4().hex
        try:
            with db() as con:
                con.execute('BEGIN IMMEDIATE')
                row=con.execute('SELECT * FROM executions WHERE id=?',(job_id,)).fetchone()
                if not row or row['state']!='pending':return
                study=con.execute('SELECT busy_token,revision FROM pbl_studies WHERE id=?',(row['study_id'],)).fetchone()
                if not study or study['busy_token']!=job_id or study['revision']!=row['expected_revision']:
                    con.execute("UPDATE executions SET state='unknown',detail=?,updated_at=? WHERE id=?",('项目已变化，未启动这次检查。',now(),job_id));con.execute('UPDATE pbl_studies SET busy_token=NULL,busy_until=NULL WHERE id=? AND busy_token=?',(row['study_id'],job_id));return
                con.execute("UPDATE executions SET state='running',worker_token=?,updated_at=? WHERE id=? AND state='pending'",(token,now(),job_id))
                con.execute('UPDATE pbl_studies SET busy_until=? WHERE id=?',(time.time()+45,row['study_id']))
            from .service import evaluate
            evaluate(row['study_id'],row['expected_revision'],job_id,_execution_id=job_id,_worker_token=token,_executor=executor)
        except Exception:
            _uncertain(job_id,token)


def _dispatch_worker(*args):
    try:_worker(*args)
    finally:_capacity.release()


def enqueue(study_id,expected_revision,request_id):
    from .service import require
    with db() as con:
        require(con,study_id)
        previous=con.execute('SELECT * FROM executions WHERE study_id=? AND request_id=?',(study_id,request_id)).fetchone()
        if previous:
            if previous['expected_revision']!=expected_revision:raise learning.Conflict('相同请求标识不能用于不同项目版本。')
            return public_job(con,previous)
    if not runtime.status()['available']:raise RuntimeError('执行服务尚未连接，未创建或运行代码检查。')
    if not _capacity.acquire(blocking=False):raise learning.Conflict('当前检查队列已满，请稍后重试。')
    dispatched=False
    try:
        with db() as con:
            con.execute('BEGIN IMMEDIATE');study=require(con,study_id)
            previous=con.execute('SELECT * FROM executions WHERE study_id=? AND request_id=?',(study_id,request_id)).fetchone()
            if previous:
                if previous['expected_revision']!=expected_revision:raise learning.Conflict('检查请求版本不一致。')
                return public_job(con,previous)
            if study['revision']!=expected_revision or decode(study['state'])['position']['stageIndex']!=4:raise learning.Conflict('请先核对项目阶段与保存版本。')
            active=con.execute("SELECT id FROM executions WHERE study_id=? AND state IN ('pending','running')",(study_id,)).fetchone()
            if active:raise learning.Conflict('本项目已有检查请求，可以继续查询。',{'kind':'execution','job_id':active['id']})
            if study['busy_token'] and (study['busy_until'] or 0)>time.time():raise learning.Conflict('项目仍在检查，请稍后查询。')
            if con.execute("SELECT COUNT(*) FROM executions WHERE state IN ('pending','running')").fetchone()[0]>=8:raise learning.Conflict('当前检查队列已满，请稍后重试。')
            code=con.execute("SELECT * FROM pbl_artifacts WHERE study_id=? AND kind='code'",(study_id,)).fetchone()
            if not code:raise learning.Conflict('请先保存代码。')
            job_id=new_id('execution');stamp=now()
            con.execute('INSERT INTO executions(id,study_id,request_id,source_sha256,state,started_at,updated_at,expected_revision,artifact_revision,detail) VALUES(?,?,?,?,?,?,?,?,?,?)',
                        (job_id,study_id,request_id,code['sha256'],'pending',stamp,stamp,expected_revision,code['revision'],'检查已排队。'))
            con.execute('UPDATE pbl_studies SET busy_token=?,busy_until=? WHERE id=?',(job_id,time.time()+120,study_id))
            response=public_job(con,con.execute('SELECT * FROM executions WHERE id=?',(job_id,)).fetchone())
        threading.Thread(target=_dispatch_worker,args=(database_path(),job_id,runtime.execute),daemon=True,name='pbl-check-'+job_id).start()
        dispatched=True
        return response
    
    finally:
        if not dispatched:_capacity.release()


def cancel(study_id,job_id):
    with db() as con:
        con.execute('BEGIN IMMEDIATE');row=_require_job(con,study_id,job_id)
        if row['state']=='cancelled':return public_job(con,row)
        if row['state'] not in ('pending','running'):raise learning.Conflict('这次检查已结束，请查看记录。')
        con.execute("UPDATE executions SET state='cancelled',detail=?,updated_at=? WHERE id=?",('已停止等待，不再采用这次检查的迟到结果。',now(),job_id))
        con.execute('UPDATE pbl_studies SET busy_token=NULL,busy_until=NULL WHERE id=? AND busy_token=?',(study_id,row['id']))
        return public_job(con,_require_job(con,study_id,job_id))


def recover():
    # One API process per local deployment. Never automatically re-run uncertain code.
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        rows=con.execute("SELECT id,study_id,request_id FROM executions WHERE state IN ('pending','running')").fetchall()
        for row in rows:
            con.execute("UPDATE executions SET state='unknown',detail=?,updated_at=? WHERE id=?",('服务中断，无法确认检查结果；未自动重新执行。',now(),row['id']))
            con.execute('UPDATE pbl_studies SET busy_token=NULL,busy_until=NULL WHERE id=? AND busy_token=?',(row['study_id'],row['id']))
    return len(rows)
