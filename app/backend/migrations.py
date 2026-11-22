"""Transactional v2 upgrade with a consistent SQLite backup before changing old files."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import sqlite3

SCHEMA_VERSION = 2
ATTEMPT_COLUMNS = {
    'lesson_id':'TEXT', 'family_id':'TEXT', 'exposure_group_id':'TEXT', 'purpose':'TEXT',
    'assistance':"TEXT NOT NULL DEFAULT 'unknown'", 'independent':'INTEGER NOT NULL DEFAULT 0',
    'correct':'INTEGER', 'misconception_id':'TEXT', 'remedy_task_id':'TEXT',
    'classification_version':"TEXT NOT NULL DEFAULT 'legacy'",
}
MATERIAL_COLUMNS = {'evidence_kind':"TEXT NOT NULL DEFAULT 'authored'", 'lesson_id':'TEXT',
                    'source_version':'INTEGER NOT NULL DEFAULT 1', 'source_sha256':'TEXT'}


def preflight_backup(path):
    path=Path(path).resolve()
    if not path.exists() or not path.stat().st_size:return None
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as source:
        tables={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables:return None
        version=source.execute('SELECT version FROM schema_meta WHERE id=1').fetchone() if 'schema_meta' in tables else None
        if version and version[0]>SCHEMA_VERSION:raise RuntimeError('数据库版本高于当前程序，请使用匹配版本。')
        if version and version[0]==SCHEMA_VERSION:return None
        folder=path.parent/'backups';folder.mkdir(parents=True,exist_ok=True)
        target=folder/(path.stem+'.pre-v1-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'-'+uuid4().hex[:8]+'.sqlite3')
        with sqlite3.connect(target) as destination:
            source.backup(destination)
            if destination.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('迁移备份校验未通过，未升级原数据库。')
    return target.name


def _columns(con,table,definitions,warnings):
    existing={r['name'] for r in con.execute('PRAGMA table_info('+table+')')}
    for name,definition in definitions.items():
        if name not in existing:con.execute('ALTER TABLE '+table+' ADD COLUMN '+name+' '+definition)
        else:warnings.append('旧结构已有字段：'+table+'.'+name)


def migrate(con,backup=None):
    from .content import TASK_MAP
    con.execute('BEGIN IMMEDIATE')
    con.execute('CREATE TABLE IF NOT EXISTS schema_meta(id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL,migrated_from INTEGER,updated_at TEXT NOT NULL,backup_file TEXT,warnings TEXT NOT NULL DEFAULT \'[]\')')
    row=con.execute('SELECT * FROM schema_meta WHERE id=1').fetchone()
    if row and row['version']==SCHEMA_VERSION:
        requirements={'attempts':set(ATTEMPT_COLUMNS),'materials':set(MATERIAL_COLUMNS),'schema_meta':{'warnings','backup_file'},'content_packs':{'pack_id','checksum'},'executions':{'id','worker_token','artifact_revision','expected_revision'}}
        for table,required in requirements.items():
            if not required<={r['name'] for r in con.execute('PRAGMA table_info('+table+')')}:raise RuntimeError('数据库标记为v2但结构不完整，未自动覆盖：'+table)
        return {'version':SCHEMA_VERSION,'migrated_from':SCHEMA_VERSION,'performed':False,'warnings':json.loads(row['warnings'])}
    if row and row['version']>SCHEMA_VERSION:raise RuntimeError('无法用旧程序打开较新的数据库。')
    warnings=[]
    _columns(con,'attempts',ATTEMPT_COLUMNS,warnings)
    _columns(con,'materials',MATERIAL_COLUMNS,warnings)
    con.execute('CREATE INDEX IF NOT EXISTS attempts_family ON attempts(session_id,family_id)')
    con.execute('CREATE INDEX IF NOT EXISTS attempts_lesson ON attempts(session_id,lesson_id,created_at)')
    con.execute('CREATE UNIQUE INDEX IF NOT EXISTS published_lesson_version ON materials(lesson_id,source_version) WHERE lesson_id IS NOT NULL')
    con.execute('CREATE TABLE IF NOT EXISTS content_packs(pack_id TEXT PRIMARY KEY,version TEXT NOT NULL,root TEXT NOT NULL,task_count INTEGER NOT NULL,objective_count INTEGER NOT NULL,checksum TEXT NOT NULL,loaded_at TEXT NOT NULL,status TEXT NOT NULL)')
    con.execute("""CREATE TABLE IF NOT EXISTS executions(
        id TEXT PRIMARY KEY,study_id TEXT NOT NULL REFERENCES pbl_studies(id),request_id TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('pending','running','passed','failed','unknown','cancelled')),
        result TEXT,started_at TEXT NOT NULL,updated_at TEXT NOT NULL,expected_revision INTEGER NOT NULL,
        artifact_revision INTEGER NOT NULL,worker_token TEXT,detail TEXT NOT NULL DEFAULT '',UNIQUE(study_id,request_id))""")
    con.execute('CREATE INDEX IF NOT EXISTS executions_study ON executions(study_id,updated_at)')
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS executions_active ON executions(study_id) WHERE state IN ('pending','running')")
    seen=set()
    for attempt in con.execute('SELECT * FROM attempts ORDER BY created_at,rowid').fetchall():
        result=json.loads(attempt['result'])
        entry=TASK_MAP.get(attempt['task_id']);task=entry[1] if entry else {}
        lesson=entry[0]['id'] if entry else result.get('lesson_id')
        family=task.get('family_id') or result.get('family_id') or attempt['task_id']
        purpose=result.get('purpose') or (entry[2] if entry else None)
        help_kind=result.get('assistance','unknown')
        correct=result.get('correct')
        if help_kind not in ('none','delivered','uncertain','unknown'):help_kind='unknown'
        if correct is not None and not isinstance(correct,bool):
            correct=None;warnings.append('历史判定类型不明确，保留原文：'+attempt['id'])
        independent=bool(result.get('independent') and correct is True and purpose=='review' and help_kind=='none' and (attempt['session_id'],family) not in seen)
        diagnosis=result.get('diagnosis') or {}
        con.execute('UPDATE attempts SET lesson_id=?,family_id=?,exposure_group_id=?,purpose=?,assistance=?,independent=?,correct=?,misconception_id=?,remedy_task_id=?,classification_version=? WHERE id=?',
                    (lesson,family,task.get('exposure_group_id') or result.get('exposure_group_id'),purpose,help_kind,int(independent),None if correct is None else int(bool(correct)),diagnosis.get('id'),diagnosis.get('remedy_task_id'),'migrated-family-v2',attempt['id']))
        seen.add((attempt['session_id'],family))
        if not entry:warnings.append('保留未匹配课程的历史作答：'+attempt['id'])
    # Keep original result JSON and every learner record intact; new columns are projections.
    con.execute('INSERT OR REPLACE INTO schema_meta(id,version,migrated_from,updated_at,backup_file,warnings) VALUES(1,?,?,?,?,?)',
                (SCHEMA_VERSION,row['version'] if row else 1,datetime.now(timezone.utc).isoformat(),backup,json.dumps(warnings,ensure_ascii=False)))
    return {'version':SCHEMA_VERSION,'migrated_from':row['version'] if row else 1,'performed':True,'backup_file':backup,'warnings':warnings}
