from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from . import service,executions
router=APIRouter(prefix='/api/pbl')
class Start(BaseModel):request_id:str=Field(min_length=8,max_length=100)
class Command(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:str=Field(min_length=8,max_length=100)
    expected_revision:int=Field(ge=1)
    kind:Literal['next','decision','plan','code','quiz']
    text:str=Field(default='',max_length=20000)
    chosen:str=Field(default='',max_length=2000)
    rationale:str=Field(default='',max_length=2000)
    artifact_sha:str=Field(default='',max_length=64)
    answers:list[int]=Field(default_factory=list,max_length=8)
class Chat(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:str=Field(min_length=8,max_length=100)
    message:str=Field(min_length=1,max_length=4000)
    review_kind:Literal['','plan','code']=''
    artifact_sha:str=Field(default='',max_length=64)
class Evaluate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    model_config=ConfigDict(extra='forbid')
    request_id:str=Field(min_length=8,max_length=100)
    expected_revision:int=Field(ge=1)
@router.get('/catalog')
def catalog():return service.catalog()
@router.post('/studies')
def start(body:Start):return service.start(body.request_id)
@router.get('/studies/{identifier}')
def detail(identifier:str):return service.detail(identifier)
@router.get('/studies/{identifier}/report')
def report(identifier:str):return service.report(identifier)
@router.post('/studies/{identifier}/run',status_code=202)
def run(identifier:str,body:Evaluate):
    try:return executions.enqueue(identifier,body.expected_revision,body.request_id)
    except RuntimeError as e:raise HTTPException(503,str(e)) from None
@router.get('/studies/{identifier}/run/{job_id}')
def run_status(identifier:str,job_id:str):return executions.read(identifier,job_id)
@router.post('/studies/{identifier}/run/{job_id}/cancel')
def cancel_run(identifier:str,job_id:str):return executions.cancel(identifier,job_id)
@router.post('/studies/{identifier}/commands')
def command(identifier:str,body:Command):return service.command(identifier,**body.model_dump())
@router.post('/studies/{identifier}/chat')
def chat(identifier:str,body:Chat):
    try:return service.chat(identifier,**body.model_dump())
    except (service.learning.NotFound,service.learning.Conflict,ValueError):raise
    except Exception:raise HTTPException(502,'林知暂时没有完成这次建议，输入已保留，可以重试。') from None
@router.post('/studies/{identifier}/evaluate')
def evaluate(identifier:str,body:Evaluate):
    try:return service.evaluate(identifier,**body.model_dump())
    except RuntimeError as e:raise HTTPException(503,str(e)) from None
