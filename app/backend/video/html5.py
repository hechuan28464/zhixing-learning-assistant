"""Bounded public HTML5 course/demo adapter: real <video>/<track>, no fixtures."""
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse
from pathlib import Path
import urllib.request,time

PREFIX='https://iandevlin.github.io/mdn/video-player-with-captions/'
COURSE_PREFIX='https://cs50.harvard.edu/python/shorts/'
COURSE_CDN='https://cdn.cs50.net/python/2023/x/shorts/'
def allowed(url):return url.startswith((PREFIX,COURSE_PREFIX,COURSE_CDN)) and not urlparse(url).query
class Player(HTMLParser):
    def __init__(self):super().__init__();self.sources=[];self.tracks=[];self.in_title=False;self.title=[]
    def handle_starttag(self,tag,attrs):
        row=dict(attrs)
        if tag=='source' and row.get('src'):self.sources.append(row)
        if tag=='track' and row.get('kind') in ('subtitles','captions') and row.get('src'):self.tracks.append(row)
        if tag=='h1':self.in_title=True
    def handle_endtag(self,tag):
        if tag=='h1':self.in_title=False
    def handle_data(self,data):
        if self.in_title:self.title.append(data)

class CourseLinks(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.headings=[];self.heading=None
    def handle_starttag(self,tag,attrs):
        row=dict(attrs)
        if tag=='a' and row.get('href'):self.links.append(row['href'])
        if tag=='h1':self.heading=[]
    def handle_data(self,data):
        if self.heading is not None:self.heading.append(data)
    def handle_endtag(self,tag):
        if tag=='h1' and self.heading is not None:self.headings.append(''.join(self.heading).strip());self.heading=None
def probe(url):
    from .media import fetch_bytes
    if not allowed(url):raise ValueError('当前公开HTML5页面不在已核验的来源范围。')
    if url.startswith(COURSE_PREFIX):
        page=CourseLinks();page.feed(fetch_bytes(url,limit=2*1024*1024).decode('utf-8'))
        links=[urljoin(url,link) for link in page.links]
        media=next((link for link in links if link.startswith(COURSE_CDN) and link.endswith('-360p.mp4')),None)
        track=next((link for link in links if link.startswith(COURSE_CDN) and link.endswith('/lang/en/'+link.split('/')[-1]) and link.endswith('.srt')),None)
        if not media or not track:raise ValueError('课程页面没有取得配对的视频与官方字幕。')
        title='CS50 Python · '+(page.headings[-1] if page.headings else '公开短课')
        info={'title':title,'author':'Harvard CS50','webpage_url':url,'subtitles':{'en':[{'ext':'srt','url':track}]},'html5_media_url':media,'duration':0}
        return info,{'title':title,'author':info['author'],'duration':0,'platform':'html5','source_url':url}
    page=Player();page.feed(fetch_bytes(url,limit=2*1024*1024).decode('utf-8'))
    media=next((urljoin(url,s['src']) for s in page.sources if s.get('type')=='video/mp4'),None)
    if not media or not allowed(media):raise ValueError('未找到可验证的视频来源。')
    tracks={}
    for track in page.tracks:
        source=urljoin(url,track['src'])
        if allowed(source):tracks.setdefault(track.get('srclang','und'),[]).append({'ext':'vtt','url':source})
    title=''.join(page.title).strip() or 'HTML5字幕视频'
    info={'title':title,'author':'Blender Foundation · MDN字幕演示','webpage_url':url,'subtitles':tracks,'html5_media_url':media,'duration':0}
    return info,{'title':title,'author':info['author'],'duration':0,'platform':'html5','source_url':url}
def download(url,folder,kind,check):
    from .media import public_network,public_address
    info,_=probe(url);source=info['html5_media_url'];public_address(urlparse(source).hostname)
    target=folder/'video.mp4';temporary=folder/'video.mp4.part';size=0;started=time.monotonic()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with public_network(),opener.open(source,timeout=20) as stream,temporary.open('wb') as out:
            while chunk:=stream.read1(32*1024):
                check();size+=len(chunk)
                if time.monotonic()-started>60:raise TimeoutError('视频文件传输较慢；已读取的原字幕保留，可以继续阅读。')
                if size>128*1024*1024:raise ValueError('视频文件超过128MB限制。')
                out.write(chunk)
        temporary.replace(target);return target
    finally:temporary.unlink(missing_ok=True)
