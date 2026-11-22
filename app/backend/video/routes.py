from pathlib import Path
from fastapi import APIRouter,Request,Query,HTTPException
from fastapi.responses import FileResponse,Response
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from ..store import db,now,new_id
from .. import service as learning
from . import service,storage,subtitles

router=APIRouter(prefix='/api/videos')
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Resolve(Strict):
    url:str=Field(min_length=1,max_length=2000)
    request_id:str=Field(min_length=8,max_length=100)
    session_id:str|None=None
class Import(Strict):
    title:str=Field(min_length=1,max_length=150)
    text:str=Field(min_length=1,max_length=500000)
    source_url:str=Field(default='',max_length=2000)
    session_id:str|None=None
    request_id:str=Field(min_length=8,max_length=100)
class Process(Strict):
    request_id:str=Field(min_length=8,max_length=100)
    frames:bool=True
    allow_asr:bool=False
    refresh_subtitles:bool=False
class Generate(Strict):request_id:str=Field(min_length=8,max_length=100)
class SubtitleVersion(Generate):text:str=Field(min_length=1,max_length=500000)
class Link(Strict):session_id:str|None=None
class Archive(Strict):archived:bool=True
class Citation(Strict):
    segment_ids:list[str]=Field(default_factory=list,max_length=50)
    generation_id:str|None=None
    published:bool=True
    kind:Literal['material','note']='material'
    request_id:str=Field(min_length=8,max_length=100)

@router.get('/runtime')
def runtime():return service.runtime()
@router.get('')
def library(query:str=Query(default='',max_length=300),status:Literal['','running','completed','failed']='',archived:bool=False,page:int=Query(default=1,ge=1,le=100000)):return service.list_assets(query,status,archived,page)
@router.post('/resolve',status_code=202)
def resolve(body:Resolve):return service.create(**body.model_dump())
@router.post('/imports')
def import_subtitle(body:Import):return service.import_subtitle(**body.model_dump())
@router.post('/uploads',status_code=202)
async def upload(request:Request,filename:str=Query(max_length=200),title:str=Query(min_length=1,max_length=150),session_id:str=''):
    owner=service.owned();suffix=Path(filename).suffix.lower()
    if suffix not in ('.mp4','.mov','.mkv','.webm','.mp3','.wav','.m4a','.ogg'):raise ValueError('请选择支持的音视频文件。')
    if int(request.headers.get('content-length','0'))>service.MAX_UPLOAD:raise HTTPException(413,'文件超过128MB限制。')
    identifier=new_id('vid');folder=storage.folder(identifier);path=folder/('upload'+suffix);size=0
    try:
        with path.open('wb') as stream:
            async for chunk in request.stream():
                size+=len(chunk)
                if size>service.MAX_UPLOAD:raise HTTPException(413,'文件超过128MB限制。')
                stream.write(chunk)
        if not size:raise ValueError('文件内容为空。')
        with db() as c:
            if session_id:learning.require_session(c,session_id)
            stamp=now()
            c.execute('INSERT INTO video_assets(id,owner,title,platform,status,session_id,upload_file,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(identifier,owner,title,'local','uploaded',session_id or None,path.name,stamp,stamp))
        return service.enqueue(identifier,'probe',new_id('upload'))
    except Exception:
        path.unlink(missing_ok=True)
        raise
@router.get('/{identifier}')
def detail(identifier:str):return service.detail(identifier)
@router.get('/{identifier}/segments')
def segments(identifier:str,page:int=Query(default=1,ge=1),query:str=Query(default='',max_length=300),ids:str|None=Query(default=None,max_length=2500)):return service.segments(identifier,page,query,ids)
@router.post('/{identifier}/process',status_code=202)
def process(identifier:str,body:Process):return service.enqueue(identifier,'process',body.request_id,{'frames':body.frames,'allow_asr':body.allow_asr,'refresh_subtitles':body.refresh_subtitles})
@router.post('/{identifier}/generate',status_code=202)
def generate(identifier:str,body:Generate):return service.enqueue(identifier,'generate',body.request_id)
@router.post('/{identifier}/cancel')
def cancel(identifier:str):return service.cancel(identifier)
@router.post('/{identifier}/subtitles')
def subtitle_version(identifier:str,body:SubtitleVersion):return service.replace_subtitles(identifier,body.text,body.request_id)
@router.post('/{identifier}/link')
def link(identifier:str,body:Link):return service.link(identifier,body.session_id)
@router.post('/{identifier}/archive')
def archive(identifier:str,body:Archive):return service.archive(identifier,body.archived)
@router.post('/{identifier}/citations')
def citation(identifier:str,body:Citation):return service.citation(identifier,**body.model_dump())
@router.get('/{identifier}/files/{filename}')
def file(identifier:str,filename:str):
    with db() as c:
        row=storage.require(c,identifier,service.owned());allowed={row['poster_file'],row['media_file']}
        allowed.update(r['file'] for r in c.execute('SELECT file FROM video_frames WHERE video_id=?',(identifier,)))
    if filename not in allowed or not filename or Path(filename).name!=filename:raise learning.NotFound('媒体文件不存在。')
    path=storage.folder(identifier)/filename
    if not path.is_file():raise learning.NotFound('媒体文件暂时不可用，原字幕仍然保留。')
    return FileResponse(path,headers={'Cache-Control':'private, max-age=3600','Vary':'Cookie','X-Content-Type-Options':'nosniff'})
@router.get('/{identifier}/export')
def export(identifier:str,kind:Literal['srt','md','zip']='md',generation_id:str=''):
    with db() as c:
        row=storage.require(c,identifier,service.owned());items=storage.rows(c,identifier,row['subtitle_version'])
    if not items:raise learning.NotFound('尚无可导出的字幕。')
    if kind=='srt':text=subtitles.srt(items);media_type='application/x-subrip'
    else:
        detail=service.detail(identifier);generation=next((g for g in detail['generations'] if g['id']==generation_id),None)
        if generation_id and not generation:raise learning.NotFound('指定的整理版本不存在。')
        if generation and generation['source_version']!=row['subtitle_version']:raise learning.Conflict('这份整理属于旧字幕版本，请选择当前版本或单独导出字幕。')
        text='# '+row['title']+'\n\n来源：'+(row['source_url'] or '用户上传／导入')+'\n\n'
        if generation:
            data=generation['data'];text+='## AI整理\n\n'+data['summary']+'\n\n'
            for part in data['sections']:text+='### '+part['title']+'\n\n'+part['body']+'\n\n'
        if kind=='zip':
            import io,zipfile,json
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as archive:
                for frame in detail['frames']:
                    name=frame['url'].rsplit('/',1)[-1];path=storage.folder(identifier)/name
                    if path.is_file():
                        archive.write(path,'images/'+name)
                        text+='![视频原帧 '+subtitles.timestamp(frame['time'])[:8]+'](images/'+name+')\n\n'
                archive.writestr('subtitles.srt',subtitles.srt(items))
                archive.writestr('sources.json',json.dumps({'video':row['source_url'],'title':row['title'],'transcript_kind':row['transcript_kind'],'source_version':row['subtitle_version'],'frames':detail['frames'],'generation':generation},ensure_ascii=False,indent=2))
                for s in items:text+='['+subtitles.timestamp(s['start'])[:8]+'] '+s['text']+'\n\n'
                archive.writestr('notes.md',text)
            return Response(data.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{identifier}-notes.zip"','Cache-Control':'no-store'})
        for s in items:text+='['+subtitles.timestamp(s['start'])[:8]+'] '+s['text']+'\n\n'
        media_type='text/markdown'
    return Response(text,media_type=media_type,headers={'Content-Disposition':f'attachment; filename="{identifier}.{kind}"','Cache-Control':'no-store'})
