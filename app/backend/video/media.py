"""Platform adapters run only in the private, single-concurrency media worker."""
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse,parse_qs,urlencode
import ipaddress,json,math,os,re,socket,subprocess,time,urllib.request

ALLOWED={'bilibili.com':'bilibili','www.bilibili.com':'bilibili','m.bilibili.com':'bilibili','b23.tv':'bilibili',
         'youtube.com':'youtube','www.youtube.com':'youtube','m.youtube.com':'youtube','youtu.be':'youtube',
         'www.douyin.com':'douyin','v.douyin.com':'douyin','douyin.com':'douyin','www.kuaishou.com':'kuaishou','v.kuaishou.com':'kuaishou','kuaishou.com':'kuaishou'}

def normalize_url(value):
    from .html5 import allowed
    if allowed(value.strip()):return value.strip(),'html5'
    match=re.search(r'https?://[^\s<>\]\[【】（）)]+',value.strip())
    if not match:raise ValueError('请输入支持的视频平台链接。')
    url=match.group(0).rstrip('。，,;；');parts=urlparse(url)
    if parts.scheme!='https' or parts.username or parts.password or parts.port not in (None,443) or parts.hostname not in ALLOWED:raise ValueError('请使用Bilibili、YouTube、抖音或快手的HTTPS公开视频链接。')
    if len(url)>1800:raise ValueError('视频链接过长。')
    platform=ALLOWED[parts.hostname]
    if platform=='bilibili' and 'bilibili.com' in parts.hostname:
        match=re.search(r'/video/(BV[0-9A-Za-z]+|av\d+)',parts.path)
        if not match:raise ValueError('请打开具体视频页面，再复制链接；合集需要选择一个分P。')
        page=parse_qs(parts.query).get('p',['1'])[0]
        if not page.isdigit() or not 1<=int(page)<=10000:raise ValueError('分P参数无效。')
        url='https://www.bilibili.com/video/'+match.group(1)+(('?p='+page) if page!='1' else '')
    elif platform=='youtube':
        if parts.hostname=='youtu.be':identifier=parts.path.strip('/')
        elif parts.path.startswith('/shorts/'):identifier=parts.path.split('/')[2]
        else:identifier=parse_qs(parts.query).get('v',[''])[0]
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',identifier):raise ValueError('请提供具体YouTube视频链接。')
        url='https://www.youtube.com/watch?'+urlencode({'v':identifier})
    else:url=parts._replace(fragment='').geturl()
    return url,platform

def public_address(host):
    addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(entry[4][0].split('%')[0]).is_global for entry in addresses):raise ValueError('视频来源地址不能访问本机或内部网络。')

@contextmanager
def public_network():
    """Guard actual connections too, including extractor redirects and CDN URLs."""
    original=socket.socket.connect;original_ex=socket.socket.connect_ex
    def guard(address):
        if isinstance(address,tuple):
            host=address[0]
            try:
                if not ipaddress.ip_address(host.split('%')[0]).is_global:raise ValueError('不允许访问内部网络地址。')
            except ValueError as error:
                if '不允许' in str(error):raise
                public_address(host)
    def connect(sock,address):guard(address);return original(sock,address)
    def connect_ex(sock,address):guard(address);return original_ex(sock,address)
    socket.socket.connect=connect;socket.socket.connect_ex=connect_ex
    try:yield
    finally:socket.socket.connect=original;socket.socket.connect_ex=original_ex

class QuietLogger:
    def debug(self,*args):pass
    def warning(self,*args):pass
    def error(self,*args):pass

def options():
    return {'quiet':True,'no_warnings':True,'logger':QuietLogger(),'noplaylist':True,'playlistend':1,'socket_timeout':15,'retries':1,
            'fragment_retries':1,'extractor_retries':1,'proxy':'','max_filesize':134217728,'cachedir':False,'ignoreerrors':False,
            'remote_components':set(),'js_runtimes':{'node':{}}}

def probe(url):
    from . import html5
    if html5.allowed(url):return html5.probe(url)
    import yt_dlp
    canonical,platform=normalize_url(url);public_address(urlparse(canonical).hostname)
    with public_network(),yt_dlp.YoutubeDL(options()) as ydl:info=ydl.extract_info(canonical,download=False)
    if info.get('_type') in ('playlist','multi_video') or info.get('entries'):raise ValueError('请提供单个视频或具体分P链接。')
    duration=float(info.get('duration') or 0)
    if not math.isfinite(duration) or duration<=0 or duration>1800 or info.get('is_live'):raise ValueError('当前支持30分钟以内、非直播的视频，请按章节选择。')
    return info,{'title':str(info.get('title') or '未命名视频')[:150],'author':str(info.get('uploader') or info.get('channel') or '')[:150],'duration':duration,'platform':platform,'source_url':canonical}

def fetch_bytes(url,limit=4*1024*1024,referer=None):
    parts=urlparse(url)
    if parts.scheme not in ('http','https') or parts.username or parts.password:raise ValueError('来源返回的下载地址无效。')
    public_address(parts.hostname)
    headers={'User-Agent':'Mozilla/5.0'}
    if referer:headers['Referer']=referer
    request=urllib.request.Request(url,headers=headers)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with public_network(),opener.open(request,timeout=20) as response:data=response.read(limit+1)
    if len(data)>limit:raise ValueError('来源文件超过当前读取限制。')
    return data

def captions(info):
    from .subtitles import parse
    for key,label in [('subtitles','platform_human'),('automatic_captions','platform_auto')]:
        mapping=info.get(key) or {}
        languages=sorted(mapping,key=lambda lang:(not lang.lower().startswith(('zh','ai-zh')),not lang.startswith('en'),lang))
        for language in languages[:3]:
            for item in sorted(mapping[language],key=lambda row:{'json':0,'srt':1,'vtt':2}.get(row.get('ext'),9)):
                if item.get('ext') not in ('json','srt','vtt'):continue
                try:return parse(fetch_bytes(item['url'],referer=info.get('webpage_url')).decode('utf-8-sig')),label
                except (ValueError,OSError,UnicodeError):continue
    return None,''

def download(url,folder,kind,check):
    from . import html5
    if html5.allowed(url):return html5.download(url,folder,kind,check)
    import yt_dlp
    def progress(status):
        check()
        if status.get('downloaded_bytes',0)>134217728:raise ValueError('视频文件超过128MB限制。')
    opts=options();opts.update({'outtmpl':str(folder/(kind+'.%(ext)s')),'progress_hooks':[progress],
        'format':'bestaudio[protocol=https]/best[protocol=https]' if kind=='audio' else 'best[ext=mp4][protocol=https]/bestvideo[ext=mp4][protocol=https]/bestvideo[protocol=https]',
        'postprocessors':[],'fixup':'never','hls_prefer_native':True})
    with public_network(),yt_dlp.YoutubeDL(opts) as ydl:
        info=ydl.extract_info(url,download=True);path=Path(ydl.prepare_filename(info))
    check()
    if not path.is_file() or path.stat().st_size>134217728:raise ValueError('没有取得可用的媒体文件。')
    return path

def run_process(args,check,timeout=180):
    import tempfile
    with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(args,stdout=output,stderr=errors,stdin=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        started=time.monotonic()
        try:
            while process.poll() is None:
                check()
                if time.monotonic()-started>timeout:raise TimeoutError('这一步处理时间较长，已停止；已完成资料保留。')
                time.sleep(.25)
            output.seek(0);errors.seek(0);out=output.read(2*1024*1024);err=errors.read(2*1024*1024)
            if process.returncode:raise RuntimeError('媒体工具没有完成处理，请检查文件格式或重试。')
            return out,err
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:process.kill();process.wait()

def local_info(path,check):
    out,_=run_process(['ffprobe','-v','error','-protocol_whitelist','file,pipe,crypto,data','-show_entries','format=duration:stream=codec_type','-of','json',str(path)],check,20)
    data=json.loads(out);duration=float(data.get('format',{}).get('duration',0));has_video=any(s.get('codec_type')=='video' for s in data.get('streams',[]))
    if not math.isfinite(duration) or not 0<duration<=1800:raise ValueError('当前支持30分钟以内的音视频，请按章节拆分。')
    return duration,has_video

def extract_frames(path,folder,segments,check):
    import hashlib
    out,err=run_process(['ffmpeg','-hide_banner','-nostdin','-y','-protocol_whitelist','file,pipe,crypto,data','-i',str(path),'-an','-vf',r'select=eq(n\,0)+gt(scene\,0.28),scale=960:-2,showinfo','-fps_mode','vfr','-frames:v','10',str(folder/'frame-%03d.jpg')],check,240)
    times=[float(v) for v in re.findall(rb'\bn:\s*\d+.*?pts_time:([0-9.]+)',err)]
    files=sorted(folder.glob('frame-*.jpg'));result=[]
    for file,at in zip(files,times):
        closest=min(segments,key=lambda s:abs(s['start']-at)) if segments else None
        result.append({'time':at,'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'segment_ids':[closest['id']] if closest else []})
    if len(result)<6 and segments:
        duration=segments[-1]['end']
        for i in range(1,8):
            at=round(duration*i/8,3)
            if any(abs(item['time']-at)<2 for item in result):continue
            file=folder/f'sample-{i:03}.jpg'
            run_process(['ffmpeg','-hide_banner','-nostdin','-y','-protocol_whitelist','file,pipe,crypto,data','-ss',str(at),'-i',str(path),'-frames:v','1','-vf','scale=960:-2',str(file)],check,30)
            if file.is_file():result.append({'time':at,'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'segment_ids':[]})
    result.sort(key=lambda item:item['time'])
    for i,item in enumerate(result):
        end=result[i+1]['time'] if i+1<len(result) else float('inf')
        item['segment_ids']=[s['id'] for s in segments if item['time']<=s['start']<end]
    if not result:raise ValueError('没有取得带时间戳的实际视频帧。')
    return result

def transcribe(path,target,model_root,check):
    import sys
    args=[sys.executable,'-m','backend.video.worker','--transcribe',str(path),'--output',str(target),'--models',str(model_root)]
    run_process(args,check,900)
    data=json.loads(target.read_text(encoding='utf-8'))
    if not data:raise ValueError('没有识别到有效语音，请导入字幕或换一份录音。')
    return data

def playable_video(video,folder,url,check):
    out,_=run_process(['ffprobe','-v','error','-protocol_whitelist','file,pipe,crypto,data','-show_entries','stream=codec_type','-of','json',str(video)],check,20)
    streams=json.loads(out).get('streams',[])
    if any(s.get('codec_type')=='audio' for s in streams):return video
    audio=next((p for p in folder.glob('audio.*') if p.suffix in ('.m4a','.mp3','.webm','.ogg','.mp4')),None)
    if not audio:
        if not url:return video
        audio=download(url,folder,'audio',check)
    output=folder/'playback.mp4'
    run_process(['ffmpeg','-hide_banner','-nostdin','-y','-protocol_whitelist','file,pipe,crypto,data','-i',str(video),'-protocol_whitelist','file,pipe,crypto,data','-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output)],check,120)
    if output.stat().st_size>134217728:raise ValueError('合并后的媒体文件超过当前播放限制。')
    return output
