"""Capture only the visible in-app browser region of the ChatGPT window."""
from pathlib import Path
import json,subprocess,time,datetime
r=Path(__file__).resolve().parents[1];out=r/'recordings/native';out.mkdir(parents=True,exist_ok=True)
stop=out/'stop-recording.flag';stop.unlink(missing_ok=True)
video=out/'内置浏览器实录-正式.mp4'
command=['ffmpeg','-hide_banner','-loglevel','warning','-y','-f','gdigrab','-draw_mouse','1','-framerate','30','-offset_x','0','-offset_y','294','-video_size','2560x1104','-i','title=ChatGPT','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
with (out/'recording.log').open('wb') as log:
    p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    meta={'pid':p.pid,'started_epoch':time.time(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'Codex in-app browser window only','crop':{'x':0,'y':294,'width':2560,'height':1104},'output':str(video)}
    (out/'capture.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
    while p.poll() is None:
        if stop.exists() or time.time()-meta['started_epoch']>1200:
            p.stdin.write(b'q\n');p.stdin.flush();break
        time.sleep(.2)
    code=p.wait(timeout=30);meta.update(exit_code=code,duration=time.time()-meta['started_epoch']);(out/'capture.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
