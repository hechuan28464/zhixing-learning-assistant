from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import importlib.util,json,subprocess,shutil
r=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('voice_client',r/'production/token-plan-voice.py');voice=importlib.util.module_from_spec(spec);spec.loader.exec_module(voice)
plan=json.loads((r/'src/plan.json').read_text(encoding='utf8'));audio=r/'public/audio/aliyun';audio.mkdir(parents=True,exist_ok=True)
asr=r/'production/voice-asr';asr.mkdir(exist_ok=True)
legacy=r/'out/legacy-windows-audio';legacy.mkdir(exist_ok=True)
def one(scene,index,text):
    name=f'{scene}-{index}';mp3=audio/(name+'.mp3');receipt=mp3.with_suffix('.receipt.json')
    if not mp3.exists():voice.tts(text,mp3,'longanlufeng')
    elif not receipt.exists():raise RuntimeError('Existing audio has no verified provider receipt: '+name)
    destination=r/f'public/audio/{name}.wav'
    if destination.exists() and not (legacy/destination.name).exists():shutil.copyfile(destination,legacy/destination.name)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(mp3),'-ar','24000','-ac','1',str(destination)],check=True)
    out=asr/(name+'.json')
    if not out.exists():voice.asr(mp3,out)
    return {'id':name,'tts':'qwen-audio-3.0-tts-plus','voice':'longanlufeng','asr':'qwen-audio-3.0-asr-flash','characters':len(text)}
results=[];failures=[]
with ThreadPoolExecutor(max_workers=3) as pool:
    future={pool.submit(one,s['id'],i,text):(s['id'],i) for s in plan for i,text in enumerate(s['sentences'])}
    for f in as_completed(future):
        try:result=f.result();results.append(result);print('Natural voice + ASR ready: '+result['id'],flush=True)
        except Exception as e:failures.append({'id':future[f],'error':str(e)[:300]});print('Voice item failed: '+str(future[f]),flush=True)
(r/'production/aliyun-voice-manifest.json').write_text(json.dumps({'completed':results,'failed':failures},ensure_ascii=False,indent=2),encoding='utf8')
if failures:raise SystemExit(1)
print('Verified natural male narration complete.',flush=True)
