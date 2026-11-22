"""Token Plan TTS/ASR authoring client. Never exposes credentials or signed URLs."""
from pathlib import Path
import argparse,base64,hashlib,json,time,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[2]
BASE='https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services'
def config():
    p=ROOT/'.env.voice.local'
    return dict(line.split('=',1) for line in p.read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.startswith('#'))
def request(path,payload):
    key=config()['TOKEN_PLAN_API_KEY'];started=time.monotonic()
    req=urllib.request.Request(BASE+path,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=300) as r:data=json.load(r)
    except urllib.error.HTTPError as e:
        try:body=json.loads(e.read().decode())
        except Exception:body={}
        raise RuntimeError(json.dumps({'http_status':e.code,'code':body.get('code'),'message':str(body.get('message',''))[:180].replace(key,'[hidden]')})) from None
    return data,round(time.monotonic()-started,3)
def tts(text,output,voice='longanlufeng'):
    payload={'model':'qwen-audio-3.0-tts-plus','input':{'text':text,'voice':voice,'format':'mp3','sample_rate':24000}}
    data,seconds=request('/audio/tts/SpeechSynthesizer',payload)
    url=data.get('output',{}).get('audio',{}).get('url')
    if not url:raise RuntimeError('TTS did not return audio URL: '+str(data.get('code','unknown')))
    req=urllib.request.Request(url)
    with urllib.request.urlopen(req,timeout=90) as r:audio=r.read()
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(audio)
    report={'model':payload['model'],'voice':voice,'seconds':seconds,'usage':data.get('usage'),'request_id':data.get('request_id'),'file':str(output),'bytes':len(audio),'sha256':hashlib.sha256(audio).hexdigest()}
    output.with_suffix('.receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');return report
def asr(file,output):
    file=Path(file);ext=file.suffix.lstrip('.');mime='audio/mpeg' if ext=='mp3' else 'audio/'+ext
    payload={'model':'qwen-audio-3.0-asr-flash','input':{'messages':[{'role':'user','content':[{'type':'input_audio','input_audio':{'data':'data:'+mime+';base64,'+base64.b64encode(file.read_bytes()).decode()}}]}]},'parameters':{'format':ext,'language_hints':['zh']}}
    data,seconds=request('/aigc/multimodal-generation/generation',payload)
    report={'model':payload['model'],'seconds':seconds,'output':data.get('output'),'usage':data.get('usage'),'request_id':data.get('request_id')}
    Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');return {'ok':True,'seconds':seconds,'report':str(output),'usage':data.get('usage')}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['tts','asr']);p.add_argument('--text');p.add_argument('--input');p.add_argument('--voice',default='longanlufeng');p.add_argument('--output',required=True);a=p.parse_args()
    try:print(json.dumps(tts(a.text, a.output,a.voice) if a.operation=='tts' else asr(a.input,a.output),ensure_ascii=False))
    except Exception as e:print(json.dumps({'ok':False,'error':str(e)[:400]},ensure_ascii=False));raise SystemExit(1)
