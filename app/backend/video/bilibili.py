"""Bilibili signed CC and Protobuf track discovery; no browser-cookie scraping.

Protocol references: ccBilly-aipm/bilibili-ai-subtitle (MIT) FLOW_CN;
ymt200120/bili-subtitle (MIT) PROTOCOL. This is an independent adapter.
"""
import hashlib,json,os,re,time,urllib.parse,urllib.request
from pathlib import Path
from . import media,subtitles

def configured_cookie():
    configured=os.getenv('STUDY_BILIBILI_COOKIE_FILE','')
    if not configured:return ''
    path=Path(configured)
    if not path.is_file() or path.stat().st_size>100000:raise ValueError('B站字幕配置文件不可用。')
    text=path.read_text(encoding='utf-8-sig').strip();value=''
    if text.startswith('{'):
        data=json.loads(text);value=data.get('SESSDATA','')
    else:
        for line in text.splitlines():
            cols=line.split('\t')
            if len(cols)>=7 and cols[-2]=='SESSDATA':value=cols[-1];break
        if not value:
            match=re.search(r'(?:^|[;\n])\s*(?:BILIBILI_)?SESSDATA\s*=\s*([^;\r\n]+)',text)
            if match:value=match.group(1).strip().strip('"\'')
    if not value or '\r' in value or '\n' in value:raise ValueError('B站字幕配置中没有可用的SESSDATA。')
    return 'SESSDATA='+value

def request(path,params,cookie=''):
    url='https://api.bilibili.com/'+path+'?'+urllib.parse.urlencode(params)
    headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.bilibili.com/'}
    if cookie:headers['Cookie']=cookie
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with media.public_network(),opener.open(urllib.request.Request(url,headers=headers),timeout=18) as response:
        data=response.read(3*1024*1024+1)
    if len(data)>3*1024*1024:raise ValueError('字幕元信息超过读取范围。')
    return data

def varint(data,pos):
    value=0
    for shift in range(0,70,7):
        if pos>=len(data):raise ValueError('字幕元信息不完整。')
        b=data[pos];pos+=1;value|=(b&127)<<shift
        if not b&128:return value,pos
    raise ValueError('字幕元信息格式无效。')

def fields(data):
    pos=0
    while pos<len(data):
        tag,pos=varint(data,pos);wire=tag&7;number=tag>>3
        if not number:raise ValueError('字幕元信息字段无效。')
        if wire==0:value,pos=varint(data,pos)
        elif wire==2:
            size,pos=varint(data,pos)
            if size>len(data)-pos:raise ValueError('字幕元信息长度无效。')
            value=data[pos:pos+size];pos+=size
        elif wire in (1,5):
            size=8 if wire==1 else 4
            if size>len(data)-pos:raise ValueError('字幕元信息长度无效。')
            value=data[pos:pos+size];pos+=size
        else:raise ValueError('不支持的字幕元信息字段。')
        yield number,wire,value

def protobuf_tracks(data):
    result=[]
    for number,wire,body in fields(data):
        if number!=1 or wire!=2:continue
        for field,kind,value in fields(body):
            if field!=3 or kind!=2:continue
            track={}
            for n,w,v in fields(value):
                if n in (3,4,5) and w==2:track[{3:'lan',4:'lan_doc',5:'subtitle_url'}[n]]=v.decode('utf-8')
            if track.get('subtitle_url'):result.append(track)
    return result

def signed(params,cookie):
    nav=json.loads(request('x/web-interface/nav',{},cookie)).get('data',{}).get('wbi_img',{})
    key=''.join(Path(urllib.parse.urlparse(nav.get(field,'')).path).stem for field in ('img_url','sub_url'))
    order=[46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]
    if len(key)<64:raise ValueError('暂未取得字幕接口签名信息。')
    salt=''.join(key[i] for i in order)[:32];params={**params,'wts':int(time.time())}
    params={k:re.sub(r"[!'()*]",'',str(v)) for k,v in sorted(params.items())}
    params['w_rid']=hashlib.md5((urllib.parse.urlencode(params)+salt).encode()).hexdigest()
    return params

def _extract_with_cookie(url,cookie=''):
    canonical,_=media.normalize_url(url);match=re.search(r'/video/(BV[\w]+|av\d+)',canonical)
    if not match:return None,'','请展开短链接后读取平台字幕。'
    identifier=match.group(1);params={'bvid':identifier} if identifier.startswith('BV') else {'aid':identifier[2:]}
    view=json.loads(request('x/web-interface/view',params,cookie))
    if view.get('code')!=0:return None,'','视频信息未完整读取，不能确认字幕状态。'
    video=view['data'];page=int(urllib.parse.parse_qs(urllib.parse.urlparse(canonical).query).get('p',['1'])[0]);pages=video.get('pages') or []
    if not pages or page>len(pages):return None,'','指定的分P不存在。'
    cid=pages[page-1]['cid'];binding={'aid':video['aid'],'cid':cid,'bvid':video['bvid']};tracks=[];needs_login=False;errors=0
    try:
        response=json.loads(request('x/player/wbi/v2',signed(binding,cookie),cookie))
        if response.get('code')==0:
            detail=response.get('data',{});needs_login=bool(detail.get('need_login_subtitle'));tracks=detail.get('subtitle',{}).get('subtitles') or []
        else:errors+=1
    except (ValueError,OSError):errors+=1
    if not tracks:
        params={'oid':cid,'pid':video['aid'],'context_ext':'{"video_type":1}','type':1,'cur_production_type':0,'preferred_language':'ai-zh','playlist_switch':0}
        try:tracks=protobuf_tracks(request('x/v2/subtitle/web/view',params,cookie))
        except (ValueError,OSError):errors+=1
    body_failures=0;duration_mismatch=False
    for track in sorted(tracks,key=lambda t:(not t.get('lan','').startswith(('zh','ai-zh')),bool(t.get('ai_type') or t.get('lan','').startswith('ai-')))):
        source=track.get('subtitle_url','')
        if source.startswith('//'):source='https:'+source
        host=urllib.parse.urlparse(source).hostname or ''
        if not (host.endswith('.hdslb.com') or host.endswith('.bilibili.com')):continue
        try:
            items=subtitles.parse(media.fetch_bytes(source,referer='https://www.bilibili.com/').decode('utf-8'))
            if items[-1]['end']>pages[page-1].get('duration',video['duration'])+10:duration_mismatch=True;continue
            return items,'platform_auto' if track.get('ai_type') or track.get('lan','').startswith('ai-') else 'platform_human',''
        except (ValueError,OSError,UnicodeError):body_failures+=1
    if duration_mismatch:return None,'','取得的字幕时间范围与当前视频不一致，未发布该结果；原有资料保留'
    if body_failures:return None,'','已发现平台字幕轨道，但正文读取未成功，可能与网络或平台返回的地址格式有关'
    if tracks:return None,'','已发现平台字幕轨道，但暂未取得可下载的正文地址；原有资料保留'
    if needs_login:return None,'','平台字幕接口要求有效B站登录态，匿名请求不能读取本视频的字幕；这不表示视频没有字幕'
    return None,'','平台字幕接口读取失败，原视频字幕状态未确认' if errors else '当前账号暂未取得可用字幕轨道'

def extract(url):
    # Public tracks must work without any credential file. Authorized fallback is
    # attempted only after the public route has actually failed to yield captions.
    items,kind,reason=_extract_with_cookie(url,'')
    if items:return items,kind,reason
    try:cookie=configured_cookie()
    except (ValueError,OSError):return None,'',reason+'；可选的私有字幕配置暂不可用'
    return _extract_with_cookie(url,cookie) if cookie else (items,kind,reason)
