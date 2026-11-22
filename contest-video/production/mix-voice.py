from pathlib import Path
import json,wave,array
r=Path(__file__).resolve().parents[1];t=json.loads((r/'src/timeline.json').read_text(encoding='utf8'));rate=24000
track=array.array('h',[0])*round(t['total']/30*rate)
for s in t['shots']:
 for cue in s['audio']:
  with wave.open(str(r/'public'/cue['src'])) as f:
   assert f.getframerate()==rate and f.getnchannels()==1 and f.getsampwidth()==2
   data=array.array('h');data.frombytes(f.readframes(f.getnframes()))
  start=round(cue['from']/30*rate);track[start:start+len(data)]=data
with wave.open(str(r/'public/audio/narration.wav'),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(track.tobytes())
print('Built exact timeline narration:',len(track)/rate,'seconds')
