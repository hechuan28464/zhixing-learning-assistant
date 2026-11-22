from pathlib import Path
import json,wave,math
r=Path(__file__).resolve().parents[1];plan=json.loads((r/'src/plan.json').read_text(encoding='utf8'));fps=30
cursor=0;caps=[];shots=[]
def stamp(seconds):
 ms=round(seconds*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
for scene in plan:
 start=cursor;offset=65 if scene['id']=='intro' else 20;audio=[]
 for i,line in enumerate(scene['sentences']):
  file=r/f'public/audio/{scene["id"]}-{i}.wav'
  with wave.open(str(file)) as w:seconds=w.getnframes()/w.getframerate()
  frames=math.ceil(seconds*fps);audio.append({'from':start+offset,'duration':frames,'src':f'audio/{file.name}','text':line})
  # Break subtitles at punctuation, evenly timed within this actual sentence.
  import re
  chunks=[s for s in re.findall(r'[^，。；：！？]+[，。；：！？]?',line) if s.strip()];groups=[];buf=''
  for chunk in chunks:
   if len(buf)+len(chunk)>28 and buf:groups.append(buf);buf=''
   buf+=chunk
  if buf:groups.append(buf)
  consumed=0
  for j,chunk in enumerate(groups):
   dur=frames-consumed if j==len(groups)-1 else round(frames*len(chunk)/len(line));caps.append({'from':start+offset+consumed,'duration':dur,'text':chunk});consumed+=dur
  offset+=frames+12
 duration=max(240,offset+35)
 if scene['id']=='outro':duration+=60
 shot={**scene,'from':start,'duration':duration,'audio':audio};shots.append(shot);cursor+=duration
assert cursor<=360*fps,f'Video too long: {cursor/fps:.2f}s'
timeline={'fps':fps,'width':1920,'height':1080,'total':cursor,'shots':shots,'captions':caps,'bgm':False,'voice':'Microsoft Yaoyao local TTS'}
(r/'src/timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf8')
(r/'production/旁白与字幕.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(c["from"]/fps)} --> {stamp((c["from"]+c["duration"])/fps)}\n{c["text"]}' for i,c in enumerate(caps)),encoding='utf8')
(r/'production/最终分镜.md').write_text('# 最终分镜\n\n|镜头|时间|功能|素材|\n|---|---|---|---|\n'+'\n'.join(f'|{s["id"]}|{s["from"]/fps:.2f}—{(s["from"]+s["duration"])/fps:.2f}秒|{s["title"]}|{", ".join(s["images"])}|' for s in shots),encoding='utf8')
print(json.dumps({'seconds':cursor/fps,'frames':cursor,'shots':len(shots),'subtitle_segments':len(caps)}))
