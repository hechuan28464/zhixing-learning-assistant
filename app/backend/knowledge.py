"""A source-backed local library. Pending memories never become tutor facts."""
import re
from hashlib import sha256

from . import service
from .content import LESSONS, TASK_MAP
from .store import db, decode, encode, event, new_id, now, attempt_result

KINDS={'material':'资料','note':'笔记','record':'学习记录','conversation':'对话','memory':'学习记忆'}


def publish_lessons(con):
    for lesson in LESSONS:
        text='\n\n'.join(p['title']+'\n'+p['text'] for p in lesson['sections'])
        if lesson.get('reference'):
            reference=lesson['reference'];text+='\n\n课程依据\n'+reference['title']+'\n'+reference['url']+'\n'+reference['usage']
        digest=sha256(text.encode()).hexdigest()
        previous=con.execute('SELECT * FROM materials WHERE lesson_id=? ORDER BY source_version DESC LIMIT 1',(lesson['id'],)).fetchone()
        if previous and previous['source_sha256']==digest:continue
        version=previous['source_version']+1 if previous else 1
        con.execute('INSERT INTO materials(id,session_id,title,text,source,created_at,archived,evidence_kind,lesson_id,source_version,source_sha256) VALUES(?,NULL,?,?,?,?,0,?,?,?,?)',
                    ('lesson_'+lesson['id']+'_'+digest,lesson['title'],text,'自编示例讲义 · v'+str(version),now(),'authored',lesson['id'],version,digest))


def published_lesson(con,lesson_id):
    row=con.execute('SELECT * FROM materials WHERE lesson_id=? AND archived=0 ORDER BY source_version DESC LIMIT 1',(lesson_id,)).fetchone()
    return dict(row) if row else None


def _published_entry(material,session_id=None,space_title='已发布课程讲义'):
    return dict(key='material:'+material['id'],kind='material',type_label='资料',title=material['title'],text=material['text'],source=material['source'],
                updated_at=material['created_at'],session_id=session_id,space_title=space_title,lesson_id=material['lesson_id'],published=True,
                material_id=material['id'],evidence_kind='authored',verification='published_curriculum',source_version=material['source_version'],source_sha256=material['source_sha256'])


def _put(entries, kind, identifier, title, text, source, timestamp, session_id=None, **extra):
    entries.append(dict(key=f'{kind}:{identifier}',kind=kind,type_label=KINDS[kind],title=title,
                        text=text,source=source,updated_at=timestamp,session_id=session_id,**extra))


def _entries(con, session_id=None):
    if session_id:service.require_session(con,session_id)
    from .video.service import knowledge_entries
    entries=knowledge_entries(con,session_id)
    sessions={r['id']:dict(r) for r in con.execute('SELECT * FROM sessions')}
    visible=lambda sid:sid is None or session_id is None or sid==session_id
    for row in con.execute('SELECT * FROM materials WHERE archived=0 AND lesson_id IS NULL'):
        r=dict(row)
        if visible(r['session_id']):_put(entries,'material',r['id'],r['title'],r['text'],r['source'] or '手动录入',r['created_at'],r['session_id'],evidence_kind=r['evidence_kind'],verification='user_supplied',material_id=r['id'])
    # Published content appears only for a course the learner actually started.
    for sid,s in sessions.items():
        if not visible(sid):continue
        for lesson in LESSONS:
            if lesson['course_id']!=s['course_id']:continue
            material=published_lesson(con,lesson['id'])
            if material:entries.append(_published_entry(material,sid,s['title']))
    for row in con.execute('SELECT * FROM notes WHERE archived=0'):
        r=dict(row)
        if visible(r['session_id']):_put(entries,'note',r['id'],r['title'],r['text'],'灵感笔记',r['updated_at'],r['session_id'])
    for row in con.execute('SELECT * FROM messages'):
        r=dict(row)
        from .auth import REQUEST_USER
        if decode(r['metadata'],{}).get('owner') and decode(r['metadata'],{}).get('owner')!=REQUEST_USER.get():continue
        if not visible(r['session_id']):continue
        author='我' if r['role']=='user' else '林知'
        title=re.sub(r'[*#>`]','',r['content'].strip().split('\n')[0])[:28]
        _put(entries,'conversation',r['id'],author+'：'+title,r['content'],'学习对话 · '+author,r['created_at'],r['session_id'],role=r['role'],references=decode(r['metadata'],{}).get('references',[]))
    # Saved project versions have stable citation identities; editing does not rewrite history.
    for row in con.execute('SELECT a.*,s.session_id FROM pbl_artifact_versions a JOIN pbl_studies s ON s.id=a.study_id'):
        r=dict(row)
        if not visible(r['session_id']):continue
        name='项目计划' if r['kind']=='plan' else '项目代码'
        _put(entries,'record','pbl-'+r['study_id']+'-'+r['kind']+'-'+str(r['revision']),name+' · 第'+str(r['revision'])+'版',r['text'],'项目保存产物 · 不代表运行通过',r['updated_at'],r['session_id'])
    for row in con.execute('SELECT * FROM attempts'):
        r=dict(row)
        if not visible(r['session_id']):continue
        result=attempt_result(r); task=TASK_MAP.get(r['task_id'])
        title=task[0]['title'] if task else '已保存任务'
        next_step=result.get('next_step')
        next_text=(next_step.get('text') or next_step.get('reason') or next_step.get('title') or result.get('next_step_reason','')) if isinstance(next_step,dict) else (next_step or result.get('next_step_reason',''))
        text='任务：'+(task[1]['prompt'] if task else r['task_id'])+'\n\n我的作答：\n'+r['response']+'\n\n记录反馈：'+result.get('label','待核查')+'\n'+next_text
        _put(entries,'record',r['id'],title+' · '+result.get('label','作答记录'),text,'实际作答记录',r['created_at'],r['session_id'])
    from .video.service import note_entries
    for note in note_entries(con):
        if visible(note['session_id']):_put(entries,'note',note['id'],note['title'],note['text'],'视频摘录',note['updated_at'],note['session_id'])
    bykey={r['key']:r for r in entries}
    for row in con.execute('SELECT * FROM memories'):
        r=dict(row)
        if not visible(r['session_id']):continue
        source=bykey.get('conversation:'+r['source_id'])
        if not source:continue
        _put(entries,'memory',r['id'],r['title'],r['text'],'对话原文 · 待确认建议' if r['status']=='pending' else '对话原文 · 学习记忆',r['updated_at'],r['session_id'],
             status=r['status'],version=r['version'],source_key=source['key'],quote=r['quote'],source_title=source['title'])
    for entry in entries:
        entry['space_title']=sessions.get(entry['session_id'],{}).get('title','公共资料')
        entry['evidence_label']={'self_reported':'自报，未经核验','external_record':'外部记录，未经核验','official_doc':'官方资料类型，来源待核对'}.get(entry.get('evidence_kind'),'')
    return entries


def _tokens(query):
    tokens=re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+',query.lower())
    for token in list(tokens):
        if len(token)>3 and re.search(r'[\u3400-\u9fff]',token):tokens.extend(token[i:i+2] for i in range(len(token)-1))
    return list(dict.fromkeys(tokens))


def library(query='',kind='',session_id=None,include_inactive=False,limit=100,offset=0):
    with db() as con:entries=_entries(con,session_id)
    active=[e for e in entries if e['kind']!='memory' or e['status'] in ('pending','confirmed') or include_inactive]
    counts={k:sum(e['kind']==k for e in active) for k in KINDS}
    tokens=_tokens(query);results=[]
    for e in active:
        if kind and kind!=e['kind']:continue
        content=(e['title']+' '+e['text']+' '+e['source']).lower()
        score=sum(3 if t in e['title'].lower() else 1 for t in tokens if t in content)
        if tokens and not score:continue
        text=e['text'];pos=next((text.lower().find(t) for t in tokens if t in text.lower()),0)
        snippet=text[max(0,pos-40):max(0,pos-40)+200]
        results.append({k:v for k,v in e.items() if k!='text'}|{'snippet':snippet,'score':score})
    results.sort(key=lambda e:(e['score'],e['updated_at']),reverse=True)
    memories=[{k:v for k,v in e.items() if k!='text'}|{'snippet':e['text'][:200]} for e in active if e['kind']=='memory' and e['status']=='pending'][:3]
    return {'items':results[offset:offset+limit],'total':len(results),'counts':counts,'synced_at':now(),'memory_suggestions':memories,
            'relations':[{'from':e['key'],'to':e['source_key'],'type':'source','label':'对话来源'} for e in active if e['kind']=='memory'],
            'limit':limit,'offset':offset,'query':query}


def read_entry(key,session_id=None):
    if key.startswith('video:'):
        from .video.service import read_citation
        entry=read_citation(key.removeprefix('video:'),session_id)
        entry['paragraphs']=[{'number':i+1,'text':p,'locator':key+'#p'+str(i+1)} for i,p in enumerate(entry['text'].split('\n\n'))]
        return entry
    with db() as con:entry=next((e for e in _entries(con,session_id) if e['key']==key),None)
    if not entry and key.startswith('material:'):
        identifier=key.removeprefix('material:')
        with db() as con:
            material=con.execute('SELECT * FROM materials WHERE id=? AND lesson_id IS NOT NULL AND archived=0',(identifier,)).fetchone()
            owner=None
            if '/' in identifier:
                owner,lid=identifier.split('/',1)
                scope=service.require_session(con,owner)
                if session_id and owner!=session_id:raise service.NotFound('引用不属于当前学习空间。')
                if not any(l['id']==lid and l['course_id']==scope['course_id'] for l in LESSONS):raise service.NotFound('课程引用不存在。')
                material=con.execute('SELECT * FROM materials WHERE lesson_id=? AND archived=0 ORDER BY source_version LIMIT 1',(lid,)).fetchone()
            if material:
                if session_id:
                    scope=service.require_session(con,session_id)
                    if not any(l['id']==material['lesson_id'] and l['course_id']==scope['course_id'] for l in LESSONS):raise service.NotFound('课程引用不属于当前空间。')
                entry=_published_entry(dict(material),session_id or owner)
    if not entry and key.startswith('material:'):
        with db() as con:
            if session_id:service.require_session(con,session_id)
            archived=con.execute('SELECT id,session_id,title,source,created_at FROM materials WHERE id=? AND archived=1',(key.removeprefix('material:'),)).fetchone()
            if archived and (not session_id or archived['session_id'] in (None,session_id)):
                entry={'key':key,'kind':'material','type_label':'已归档资料','title':archived['title'],'source':archived['source'],'text':'','archived':True,'status':'archived','updated_at':archived['created_at'],'session_id':archived['session_id'],'space_title':'已归档'}
    if not entry:raise service.NotFound('内容不存在，或不属于当前学习空间。')
    entry['evidence_label']={'authored':'自编材料','official_doc':'官方资料类型，来源待核对','self_reported':'自报，未经核验','external_record':'外部记录，未经核验'}.get(entry.get('evidence_kind'),'')
    parts=[p.strip() for p in re.split(r'\n\s*\n',entry.get('text','')) if p.strip()]
    entry['paragraphs']=[{'number':i+1,'text':text,'locator':entry['key']+'#p'+str(i+1)} for i,text in enumerate(parts)]
    return entry


def propose_memory(con,session_id,source_id,text,quote):
    source=con.execute("SELECT * FROM messages WHERE id=? AND session_id=? AND role='user'",(source_id,session_id)).fetchone()
    text=text.strip();quote=quote.strip()
    if not source or not text or len(text)>500 or len(quote)<4 or quote not in source['content']:
        raise ValueError('记忆必须附有当前空间用户消息中的准确原文。')
    # One suggestion per source: polling, retries and revoked memories do not regenerate it.
    source_key='conversation:'+source_id
    old=con.execute('SELECT id FROM memories WHERE source_key=?',(source_key,)).fetchone()
    if old:return {'id':old['id'],'created':False}
    identifier=new_id('memory');timestamp=now()
    con.execute('INSERT INTO memories(id,session_id,title,text,source_key,source_id,quote,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                (identifier,session_id,'讲解偏好建议',text,source_key,source_id,quote,timestamp,timestamp))
    event(con,session_id,'memory_proposed','生成一条待确认的学习记忆',{'memory_id':identifier})
    return {'id':identifier,'created':True}


def capture_preference(con,session_id,source_id,message):
    # A verbatim candidate, never an inferred ability or a confirmed learner fact.
    match=re.search(r'(?:我希望|希望|我喜欢|我更喜欢|请先|以后请)[^。！？\n]{4,160}',message)
    if match:propose_memory(con,session_id,source_id,match.group(),match.group())


def change_memory(identifier,action,version):
    transitions={'confirm':('pending','confirmed'),'ignore':('pending','ignored'),'revoke':('confirmed','revoked')}
    if action not in transitions:raise ValueError('未支持的记忆操作。')
    expected,target=transitions[action]
    with db() as con:
        row=con.execute('SELECT * FROM memories WHERE id=?',(identifier,)).fetchone()
        if not row:raise service.NotFound('学习记忆不存在。')
        source=con.execute("SELECT 1 FROM messages WHERE id=? AND session_id=? AND role='user'",(row['source_id'],row['session_id'])).fetchone()
        if not source:raise service.NotFound('原始来源已不可用，不能修改这条记忆。')
        if row['version']!=version or row['status']!=expected:raise service.Conflict('记忆状态已变化，请刷新后检查。')
        updated=con.execute('UPDATE memories SET status=?,version=version+1,updated_at=? WHERE id=? AND status=? AND version=?',(target,now(),identifier,expected,version))
        if updated.rowcount!=1:raise service.Conflict('记忆已被修改，请刷新。')
        event(con,row['session_id'],'memory_'+action,{'confirm':'确认了学习记忆','ignore':'忽略了记忆建议','revoke':'撤回了学习记忆'}[action],{'memory_id':identifier})
    return read_entry('memory:'+identifier)


def confirmed_memories(session_id):
    with db() as con:
        from .auth import REQUEST_USER
        return [{'text':r['text'],'quote':r['quote'],'source_id':r['source_id']} for r in con.execute("SELECT m.*,s.metadata AS source_metadata FROM memories m JOIN messages s ON s.id=m.source_id AND s.session_id=m.session_id AND s.role='user' WHERE m.session_id=? AND m.status='confirmed' ORDER BY m.updated_at DESC LIMIT 20",(session_id,)) if not decode(r['source_metadata'],{}).get('owner') or decode(r['source_metadata'],{}).get('owner')==REQUEST_USER.get()][:10]
