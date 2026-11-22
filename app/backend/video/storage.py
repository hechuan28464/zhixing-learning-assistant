from pathlib import Path
from ..store import db,database_path,decode,now

def root():
    path=database_path().parent/'video-assets'
    path.mkdir(parents=True,exist_ok=True)
    return path

def folder(identifier):
    if not identifier.startswith('vid_') or not identifier[4:].isalnum():raise ValueError('视频资料标识无效。')
    path=root()/identifier;path.mkdir(exist_ok=True)
    return path

def initialize():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS video_assets(
          id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,source_url TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL,
          author TEXT NOT NULL DEFAULT '',duration REAL NOT NULL DEFAULT 0,status TEXT NOT NULL,session_id TEXT REFERENCES sessions(id),
          transcript_kind TEXT NOT NULL DEFAULT '',subtitle_version INTEGER NOT NULL DEFAULT 0,poster_file TEXT NOT NULL DEFAULT '',
          media_file TEXT NOT NULL DEFAULT '',upload_file TEXT NOT NULL DEFAULT '',archived INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS video_owner ON video_assets(owner,archived,updated_at);
        CREATE TABLE IF NOT EXISTS video_segments(id TEXT PRIMARY KEY,video_id TEXT NOT NULL REFERENCES video_assets(id),version INTEGER NOT NULL,
          ordinal INTEGER NOT NULL,start REAL NOT NULL,end REAL NOT NULL,text TEXT NOT NULL,UNIQUE(video_id,version,ordinal));
        CREATE TABLE IF NOT EXISTS video_jobs(id TEXT PRIMARY KEY,video_id TEXT NOT NULL REFERENCES video_assets(id),owner TEXT NOT NULL,
          kind TEXT NOT NULL,state TEXT NOT NULL,stage TEXT NOT NULL,request_id TEXT NOT NULL,payload TEXT NOT NULL,
          message TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
          UNIQUE(owner,request_id));
        CREATE INDEX IF NOT EXISTS video_jobs_queue ON video_jobs(state,created_at);
        CREATE TABLE IF NOT EXISTS video_generations(id TEXT PRIMARY KEY,video_id TEXT NOT NULL REFERENCES video_assets(id),
          revision INTEGER NOT NULL,source_version INTEGER NOT NULL,data TEXT NOT NULL,usage TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS video_frames(id TEXT PRIMARY KEY,video_id TEXT NOT NULL REFERENCES video_assets(id),time REAL NOT NULL,
          file TEXT NOT NULL,sha256 TEXT NOT NULL,segment_ids TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS video_citations(id TEXT PRIMARY KEY,video_id TEXT NOT NULL REFERENCES video_assets(id),owner TEXT NOT NULL,
          source_version INTEGER NOT NULL,segment_ids TEXT NOT NULL,generation_id TEXT,title TEXT NOT NULL,text TEXT NOT NULL,
          published INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,UNIQUE(owner,id));
        CREATE TABLE IF NOT EXISTS video_notes(id TEXT PRIMARY KEY,video_id TEXT NOT NULL REFERENCES video_assets(id),owner TEXT NOT NULL,
          citation_id TEXT NOT NULL,title TEXT NOT NULL,text TEXT NOT NULL,session_id TEXT,archived INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(owner,citation_id));
        CREATE TABLE IF NOT EXISTS video_import_requests(owner TEXT NOT NULL,request_id TEXT NOT NULL,video_id TEXT NOT NULL,sha256 TEXT NOT NULL,source_version INTEGER NOT NULL,PRIMARY KEY(owner,request_id));
        ''')
        columns={r['name'] for r in c.execute('PRAGMA table_info(video_citations)')}
        if 'source_kind' not in columns:
            c.execute("ALTER TABLE video_citations ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'unknown'")
            c.execute('UPDATE video_citations SET source_kind=(SELECT transcript_kind FROM video_assets a WHERE a.id=video_id AND a.subtitle_version=source_version) WHERE EXISTS(SELECT 1 FROM video_assets a WHERE a.id=video_id AND a.subtitle_version=source_version)')

def require(c,identifier,owner):
    from ..service import NotFound
    row=c.execute('SELECT * FROM video_assets WHERE id=? AND owner=?',(identifier,owner)).fetchone()
    if not row:raise NotFound('视频资料不存在，或不属于当前账号。')
    return dict(row)

def public_asset(row):
    item={key:value for key,value in dict(row).items() if key not in ('owner','poster_file','media_file','upload_file')}
    item['platform_label']={'html5':'公开HTML5视频','bilibili':'Bilibili','youtube':'YouTube','douyin':'抖音','kuaishou':'快手','local':'本地文件','subtitle':'导入字幕'}.get(item['platform'],'视频资料')
    item['poster_url']='/api/videos/'+item['id']+'/files/'+row['poster_file'] if row['poster_file'] else ''
    item['media_url']='/api/videos/'+item['id']+'/files/'+row['media_file'] if row['media_file'] else ''
    item['transcript_label']={'course_subtitle':'公开课程原字幕','html5_track':'公开WebVTT原字幕','platform_human':'平台人工字幕','platform_auto':'平台自动字幕','asr':'本地语音转写 · 未校对','import':'用户导入字幕'}.get(item['transcript_kind'],'')
    item['embed_url']=''
    return item

def rows(c,video_id,version):
    return [dict(row) for row in c.execute('SELECT id,ordinal,start,end,text FROM video_segments WHERE video_id=? AND version=? ORDER BY ordinal',(video_id,version))]
