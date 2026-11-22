"""Preserve source timestamps; no invented text when captions are missing."""
import html,json,re,hashlib,math

def seconds(value):
    value=value.strip().replace(',','.')
    parts=value.split(':')
    try:
        result=sum(float(n)*60**i for i,n in enumerate(reversed(parts)))
        if not math.isfinite(result) or result<0:raise ValueError()
        return result
    except (TypeError,ValueError):raise ValueError('字幕时间格式无效。') from None

def parse(text):
    if len(text)>500000:raise ValueError('字幕文本超过50万字符。')
    text=text.lstrip('\ufeff').strip();items=[]
    if text.startswith(('{','[')):
        try:
            data=json.loads(text)
            if isinstance(data,dict):data=data.get('body',data.get('segments',[]))
            if not isinstance(data,list):raise ValueError()
            for row in data:
                items.append({'start':float(row.get('start',row.get('from',0))),'end':float(row.get('end',row.get('to',0))),'text':row.get('text',row.get('content',''))})
        except (ValueError,TypeError,AttributeError):raise ValueError('字幕JSON需要包含start/end/text或B站body字段。') from None
    else:
        lines=text.splitlines();i=0
        while i<len(lines):
            match=re.match(r'\s*((?:\d+:)?\d+:\d+[.,]\d+)\s*-->\s*((?:\d+:)?\d+:\d+[.,]\d+)',lines[i])
            if not match:i+=1;continue
            start,end=map(seconds,match.groups());i+=1;words=[]
            while i<len(lines) and lines[i].strip():
                words.append(lines[i]);i+=1
            items.append({'start':start,'end':end,'text':'\n'.join(words)})
    result=[]
    for row in sorted(items,key=lambda r:r['start']):
        start,end=row['start'],row['end']
        if not all(math.isfinite(v) for v in (start,end)) or start<0 or end<=start or end>86400:raise ValueError('字幕包含无效起止时间。')
        cleaned=html.unescape(re.sub(r'<[^>]*>','',str(row['text']))).strip()
        if not cleaned:continue
        if len(cleaned)>12000:raise ValueError('单条字幕过长，请拆分后导入。')
        if result and result[-1]['text']==cleaned and start<result[-1]['end']+.2:
            result[-1]['end']=max(end,result[-1]['end']);continue
        result.append({'start':round(start,3),'end':round(end,3),'text':cleaned})
    if not result:raise ValueError('没有找到带有效时间戳的字幕，请导入SRT、VTT或字幕JSON。')
    if len(result)>20000 or sum(len(r['text']) for r in result)>200000:raise ValueError('字幕超过当前处理范围，请按章节拆分。')
    return result

def identify(video_id,version,items):
    return [{'id':'vseg_'+hashlib.sha256(f'{video_id}:{version}:{i}:{row["start"]}:{row["text"]}'.encode()).hexdigest()[:28],**row,'ordinal':i+1} for i,row in enumerate(items)]

def timestamp(value):
    milliseconds=round(float(value)*1000);hours,milliseconds=divmod(milliseconds,3600000);minutes,milliseconds=divmod(milliseconds,60000);seconds_,ms=divmod(milliseconds,1000)
    return f'{hours:02}:{minutes:02}:{seconds_:02},{ms:03}'

def srt(items):return '\n\n'.join(f'{i+1}\n{timestamp(row["start"])} --> {timestamp(row["end"])}\n{row["text"]}' for i,row in enumerate(items))+'\n'
