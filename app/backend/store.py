"""SQLite persistence; no demo learner records are seeded."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
_DATABASE=ContextVar('learning_database',default=None)
_INITIALIZE_LOCK=threading.RLock()


def database_path():
    return Path(_DATABASE.get() or os.environ.get('STUDY_DB_PATH',str(ROOT/'data/private/learning.sqlite3'))).resolve()


@contextmanager
def database_scope(path):
    token=_DATABASE.set(str(Path(path).resolve()))
    try:yield
    finally:_DATABASE.reset(token)


def now():
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix):
    return prefix+'_'+uuid4().hex


def encode(value):
    return json.dumps(value,ensure_ascii=False)


def decode(value, default=None):
    return json.loads(value) if value else default


@contextmanager
def db():
    path=database_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    connection=sqlite3.connect(path,timeout=15)
    connection.row_factory=sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=5000')
    if connection.execute('PRAGMA journal_mode').fetchone()[0].lower()!='wal':connection.execute('PRAGMA journal_mode=WAL')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _initialize_base():
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY, course_id TEXT, title TEXT NOT NULL, goal TEXT NOT NULL,
          domain TEXT NOT NULL, foundation TEXT NOT NULL DEFAULT '', daily_minutes INTEGER NOT NULL,
          plan TEXT, plan_status TEXT NOT NULL DEFAULT 'none', current_lesson TEXT,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS runs (
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
          task_id TEXT NOT NULL, task_version INTEGER NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS assistance (
          id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), kind TEXT NOT NULL,
          content TEXT NOT NULL, delivery TEXT NOT NULL DEFAULT 'offered', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attempts (
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
          run_id TEXT NOT NULL REFERENCES runs(id), task_id TEXT NOT NULL,
          request_id TEXT NOT NULL UNIQUE, response TEXT NOT NULL, result TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS materials (
          id TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(id), title TEXT NOT NULL,
          text TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS notes (
          id TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(id), title TEXT NOT NULL,
          text TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS messages (
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), role TEXT NOT NULL,
          content TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS turns (
          request_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
          input TEXT NOT NULL, status TEXT NOT NULL, result TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
          id TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(id), type TEXT NOT NULL,
          title TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS attempts_session ON attempts(session_id,created_at);
        CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id,created_at);
        CREATE INDEX IF NOT EXISTS assistance_run ON assistance(run_id);
        CREATE TABLE IF NOT EXISTS memories (
          id TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(id), title TEXT NOT NULL,
          text TEXT NOT NULL, source_key TEXT NOT NULL UNIQUE, source_id TEXT NOT NULL,
          quote TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', version INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS memories_session ON memories(session_id,status);
        CREATE TABLE IF NOT EXISTS note_requests (
          request_id TEXT PRIMARY KEY, payload TEXT NOT NULL, note_id TEXT NOT NULL REFERENCES notes(id),
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS write_requests (
          operation TEXT NOT NULL, request_id TEXT NOT NULL, payload TEXT NOT NULL,
          resource_id TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(operation,request_id)
        );
        CREATE TABLE IF NOT EXISTS pbl_studies (
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
          project_id TEXT NOT NULL, project_version TEXT NOT NULL, state TEXT NOT NULL,
          revision INTEGER NOT NULL DEFAULT 1, busy_token TEXT, busy_until REAL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(session_id,project_id,project_version)
        );
        CREATE TABLE IF NOT EXISTS pbl_artifacts (
          study_id TEXT NOT NULL REFERENCES pbl_studies(id), kind TEXT NOT NULL,
          text TEXT NOT NULL, sha256 TEXT NOT NULL, revision INTEGER NOT NULL,
          updated_at TEXT NOT NULL, PRIMARY KEY(study_id,kind)
        );
        CREATE TABLE IF NOT EXISTS pbl_events (
          id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES pbl_studies(id),
          kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pbl_commands (
          request_id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES pbl_studies(id),
          payload TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pbl_artifact_versions (
          study_id TEXT NOT NULL REFERENCES pbl_studies(id), kind TEXT NOT NULL,
          text TEXT NOT NULL, sha256 TEXT NOT NULL, revision INTEGER NOT NULL,
          updated_at TEXT NOT NULL, PRIMARY KEY(study_id,kind,revision)
        );
        CREATE TABLE IF NOT EXISTS pbl_messages (
          id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES pbl_studies(id), stage INTEGER NOT NULL,
          role TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pbl_chat_requests (
          request_id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES pbl_studies(id),
          payload TEXT NOT NULL, status TEXT NOT NULL, result TEXT, created_at TEXT NOT NULL
        );
        ''')
        con.execute('INSERT OR IGNORE INTO settings(id,payload) VALUES(1,?)',
                    (encode({'name':'学习者','daily_minutes':30,'style':'先理解，再动手'}),))


def initialize():
    from .migrations import preflight_backup,migrate
    from .packs import PACK_INFO
    from .knowledge import publish_lessons
    with _INITIALIZE_LOCK:
        backup=preflight_backup(database_path())
        _initialize_base()
        with db() as con:result=migrate(con,backup)
        from .video.storage import initialize as initialize_video
        initialize_video()
        with db() as con:
            publish_lessons(con)
            con.execute('INSERT INTO content_packs VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(pack_id) DO UPDATE SET version=excluded.version,root=excluded.root,task_count=excluded.task_count,objective_count=excluded.objective_count,checksum=excluded.checksum,status=excluded.status',
                        (PACK_INFO['id'],PACK_INFO['version'],str(ROOT/'backend/resources/contest-pack-v1'),PACK_INFO['task_count'],PACK_INFO['objective_count'],PACK_INFO['sha256'],now(),PACK_INFO['status']))
        return result


def attempt_result(row):
    item=dict(row);result=decode(item['result'],{})
    if 'classification_version' in item and item['classification_version']!='legacy':
        effective=bool(item['independent'])
        if result.get('independent') and not effective:
            result={**result,'label':'历史作答，独立条件待核对','classification_note':'原始判定保留在数据库，当前显示按题族暴露核对后的结果。'}
        result={**result,'independent':effective,'correct':None if item['correct'] is None else bool(item['correct']),'assistance':item['assistance'],
                'classification_version':item['classification_version']}
    return result


def event(con, session_id, kind, title, detail=None):
    identifier=new_id('event')
    con.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',
                (identifier,session_id,kind,title,encode(detail or {}),now()))
    return identifier


def session_or_none(con, identifier):
    row=con.execute('SELECT * FROM sessions WHERE id=?',(identifier,)).fetchone()
    if not row:return None
    result=dict(row)
    result['plan']=decode(result['plan'],[])
    return result
