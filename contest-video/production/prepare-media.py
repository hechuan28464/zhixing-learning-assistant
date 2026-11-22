from pathlib import Path
from PIL import Image
import json,hashlib,shutil
r=Path(__file__).resolve().parents[1];src=r/'public/textures/live';dst=r/'public/textures/focus';dst.mkdir(exist_ok=True)
records=json.loads((r/'production/captures.json').read_text(encoding='utf8'));latest={x['name']:x for x in records}
boxes={
 'home':(0,0,1280,720),'courses':(248,220,1240,720),'catalog':(218,45,1130,685),
 'diagnostic':(246,180,936,692),'remedy':(246,212,936,692),'review':(246,212,936,692),
 'evidence':(246,305,951,455),'history':(246,455,936,720),
 'agent':(254,100,918,520),'agent-tools':(280,298,660,425),'agent-task':(246,75,936,692),
 'knowledge':(250,215,1234,720),'citation':(250,200,1234,720),
 'video':(256,490,663,868),'video-search':(255,337,665,690),'video-page':(255,230,665,620),
 'pbl-overview':(255,150,1234,660),'graph':(255,330,1234,720)
}
manifest={}
for f in src.glob('*.png'):
 actual=f;im=Image.open(f).convert('RGB');name=f.stem;crop_box=None
 if name in boxes:
  b=boxes[name]
  if name=='video':
   # Original validated subtitle-only capture from the official course.
   actual=r.parent/'参赛交付_20261110/素材/教学视频字幕.png';im=Image.open(actual).convert('RGB');scale=1
  else:scale=im.width/latest.get(name,{'w':1280})['w']
  crop_box=tuple(round(v*scale) for v in b);im=im.crop(crop_box)
 elif name=='memory':im=im.crop((692,475,955,644))
 elif name=='pbl-plan':im=im.crop((195,160,im.width-12,min(im.height,750)))
 elif name=='pbl-run':im=im.crop((270,380,700,637))
 elif name=='graph-full':im=im.crop((250,340,im.width-25,im.height-30))
 im.save(dst/f.name,optimize=True)
 manifest[f.name]={'width':im.width,'height':im.height,'pageH':round(1920*im.height/im.width),'source':str(actual),'sha256':hashlib.sha256(actual.read_bytes()).hexdigest(),'focus_sha256':hashlib.sha256((dst/f.name).read_bytes()).hexdigest(),'crop_box':crop_box}
shutil.copyfile(r.parent/'app/public/assets/competition-v1/home/hero.png',r/'public/hero.png')
(r/'src/media.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('Prepared',len(manifest),'real UI textures and provenance.')
