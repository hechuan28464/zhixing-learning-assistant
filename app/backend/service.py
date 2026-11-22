"""Learning actions and deterministic evidence rules."""
from .content import COURSES, COURSE_MAP, LESSONS, LESSON_MAP, TASK_MAP, DECLARED_PREREQUISITES, public_course, public_lesson, public_task
from .store import db, now, new_id, encode, decode, event, session_or_none, attempt_result
from . import learning_evidence
from .packs import MISCONCEPTIONS
import re


class NotFound(ValueError): pass
class Conflict(ValueError):
    def __init__(self, message, retry=None):
        super().__init__(message)
        self.retry = retry


def require_session(con, session_id):
    result=session_or_none(con,session_id)
    if result is None:raise NotFound('学习空间不存在。')
    return result


def require_run(con, session_id, run_id):
    require_session(con,session_id)
    row=con.execute('SELECT * FROM runs WHERE id=? AND session_id=?',(run_id,session_id)).fetchone()
    if not row:raise NotFound('这次任务不属于当前学习空间，请重新打开任务。')
    return dict(row)


def states(con, session_id):
    session=require_session(con,session_id)
    attempts=[dict(row) for row in con.execute('SELECT * FROM attempts WHERE session_id=? ORDER BY created_at',(session_id,))]
    result={}
    for lesson in LESSONS:
        if lesson['course_id']!=session['course_id']:continue
        relevant=[attempt_result(a) for a in attempts if (a.get('lesson_id') or TASK_MAP.get(a['task_id'],({},))[0].get('id'))==lesson['id']]
        independent=any(a['independent'] and a['correct'] is True and a['purpose']=='review' for a in relevant)
        assisted=any(a['correct'] is True and a['assistance']!='none' for a in relevant)
        pending=any(a['status']=='pending_review' for a in relevant)
        status='independent' if independent else 'pending_review' if pending else 'assisted' if assisted else 'practicing' if relevant else 'not_started'
        result[lesson['id']]={'status':status,'label':{'independent':'有独立新题表现','pending_review':'作答待复核','assisted':'有受助完成记录','practicing':'正在练习','not_started':'尚未练习'}[status], 'attempts':len(relevant),
                             'dimensions':learning_evidence.dimensions(learning_evidence.results_for(con,session_id,lesson['id']),lesson_id=lesson['id'])}
    return result


def summaries(con):
    results=[]
    for row in con.execute('SELECT * FROM sessions ORDER BY updated_at DESC'):
        item=dict(row)
        item['plan']=decode(item['plan'],[])
        item['states']=states(con,item['id'])
        item['completed']=sum(v['status']=='independent' for v in item['states'].values())
        item['lesson_count']=len(item['states'])
        item['next']=learning_evidence.next_action(con,item)
        results.append(item)
    return results


def bootstrap():
    with db() as con:
        return {'profile':decode(con.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0]),
                'courses':[public_course(c) for c in COURSES], 'sessions':summaries(con),
                'materials':[dict(r) for r in con.execute('SELECT id,session_id,title,source,evidence_kind,created_at,length(text) AS characters FROM materials WHERE archived=0 AND lesson_id IS NULL ORDER BY created_at DESC')],
                'notes':[dict(r) for r in con.execute('SELECT * FROM notes WHERE archived=0 ORDER BY updated_at DESC')],
                'archived_materials':[dict(r) for r in con.execute('SELECT id,session_id,title,source,created_at,length(text) AS characters FROM materials WHERE archived=1 ORDER BY created_at DESC')],
                'archived_notes':[dict(r) for r in con.execute('SELECT * FROM notes WHERE archived=1 ORDER BY updated_at DESC')],
                'events':[{**dict(r),'detail':decode(r['detail'],{})} for r in con.execute('SELECT * FROM events ORDER BY created_at DESC,id DESC')]}


def retry_resource(con,operation,request_id,payload):
    if not request_id:return None
    previous=con.execute('SELECT payload,resource_id FROM write_requests WHERE operation=? AND request_id=?',(operation,request_id)).fetchone()
    if not previous:return None
    if previous['payload']!=encode(payload):raise Conflict('这次保存的内容发生了变化，请重新发起操作。')
    return previous['resource_id']


def remember_resource(con,operation,request_id,payload,identifier):
    if request_id:con.execute('INSERT INTO write_requests VALUES(?,?,?,?,?)',(operation,request_id,encode(payload),identifier,now()))


def create_session(course_id=None, title='', goal='', domain='', foundation='', daily_minutes=30,request_id=None):
    if course_id and course_id not in COURSE_MAP:raise NotFound('课程不存在。')
    course=COURSE_MAP.get(course_id)
    payload=dict(course_id=course_id,title=title,goal=goal,domain=domain,foundation=foundation,daily_minutes=daily_minutes)
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        reused=retry_resource(con,'session',request_id,payload)
        if reused:return session_detail(reused)
        if course:
            existing=con.execute('SELECT id FROM sessions WHERE course_id=? ORDER BY created_at LIMIT 1',(course_id,)).fetchone()
            if existing:
                remember_resource(con,'session',request_id,payload,existing['id'])
                return session_detail(existing['id'])
        identifier=new_id('space')
        title=(course['title'] if course else title or goal[:40]).strip()
        goal=(goal or (course['description'] if course else title)).strip()
        if not goal:raise ValueError('请先写下一个学习目标。')
        lesson=next((l['id'] for l in LESSONS if l['course_id']==course_id),None)
        timestamp=now()
        con.execute('INSERT INTO sessions(id,course_id,title,goal,domain,foundation,daily_minutes,current_lesson,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (identifier,course_id,title,goal,domain or (course['tag'] if course else '自选主题'),foundation,daily_minutes,lesson,timestamp,timestamp))
        event(con,identifier,'space_created','开始学习：'+title)
        remember_resource(con,'session',request_id,payload,identifier)
    return session_detail(identifier)


def session_detail(session_id):
    with db() as con:
        result=require_session(con,session_id)
        result['course']=public_course(COURSE_MAP[result['course_id']]) if result['course_id'] else None
        result['lessons']=[public_lesson(l) for l in LESSONS if l['course_id']==result['course_id']]
        result['states']=states(con,session_id)
        result['messages']=[{**dict(r),'metadata':decode(r['metadata'],{})} for r in con.execute('SELECT * FROM messages WHERE session_id=? ORDER BY created_at',(session_id,))]
        from .auth import REQUEST_USER
        result['messages']=[r for r in result['messages'] if not r['metadata'].get('owner') or r['metadata'].get('owner')==REQUEST_USER.get()]
        turn_status={r['request_id']:r['status'] for r in con.execute('SELECT request_id,status FROM turns WHERE session_id=?',(session_id,))}
        for message in result['messages']:
            request_id=message['metadata'].get('request_id')
            if request_id in turn_status:message['metadata']['turn_status']=turn_status[request_id]
        result['attempts']=[{**dict(r),'result':attempt_result(r)} for r in con.execute('SELECT * FROM attempts WHERE session_id=? ORDER BY created_at DESC',(session_id,))]
        return result


def select_lesson(session_id, lesson_id):
    with db() as con:
        session=require_session(con,session_id)
        lesson=LESSON_MAP.get(lesson_id)
        if not lesson or lesson['course_id']!=session['course_id']:raise NotFound('该内容不属于当前课程。')
        con.execute('UPDATE sessions SET current_lesson=?,updated_at=? WHERE id=?',(lesson_id,now(),session_id))
    return public_lesson(lesson)


def open_task(session_id, task_id):
    with db() as con:
        session=require_session(con,session_id)
        entry=TASK_MAP.get(task_id)
        if not entry or entry[0]['course_id']!=session['course_id']:raise NotFound('该任务不属于当前学习空间。')
        # Resume an unsubmitted run, preserving any offered/delivered help.
        previous=con.execute('SELECT r.id FROM runs r WHERE r.session_id=? AND r.task_id=? AND NOT EXISTS (SELECT 1 FROM attempts a WHERE a.run_id=r.id) ORDER BY r.created_at DESC LIMIT 1',(session_id,task_id)).fetchone()
        if previous:
            run_id=previous['id']
        else:
            run_id=new_id('run')
            con.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(run_id,session_id,task_id,entry[1]['version'],now()))
            event(con,session_id,'task_opened','打开任务：'+entry[0]['title'],{'run_id':run_id,'task_id':task_id})
        assistance=[dict(r) for r in con.execute('SELECT * FROM assistance WHERE run_id=? ORDER BY created_at',(run_id,))]
    return {'run_id':run_id,'task':public_task(entry[1]),'purpose':entry[2],'assistance':assistance}


def offer_assistance(con, run_id, kind, content):
    identifier=new_id('help')
    con.execute('INSERT INTO assistance(id,run_id,kind,content,created_at) VALUES(?,?,?,?,?)',(identifier,run_id,kind,content,now()))
    return identifier


def request_hint(session_id, run_id):
    with db() as con:
        run=require_run(con,session_id,run_id)
        task=TASK_MAP[run['task_id']][1]
        identifier=offer_assistance(con,run_id,'hint',task['hint'])
        event(con,session_id,'hint_offered','提供了任务提示',{'run_id':run_id,'assistance_id':identifier})
    return {'id':identifier,'content':task['hint'],'delivery':'offered'}


def acknowledge_assistance(session_id, identifier):
    with db() as con:
        row=con.execute('SELECT a.id FROM assistance a JOIN runs r ON a.run_id=r.id WHERE a.id=? AND r.session_id=?',(identifier,session_id)).fetchone()
        if not row:raise NotFound('帮助记录不存在。')
        con.execute("UPDATE assistance SET delivery='delivered' WHERE id=?",(identifier,))
    return {'ok':True}


def submit_attempt(session_id, run_id, response, request_id):
    with db() as con:
        run=require_run(con,session_id,run_id)
        previous=con.execute('SELECT * FROM attempts WHERE request_id=?',(request_id,)).fetchone()
        if previous:
            if previous['run_id']!=run_id or previous['response']!=response:raise Conflict('相同提交标识对应了不同内容，请重新提交。')
            return {**attempt_result(previous),'attempt_id':previous['id'],'reused':True}
        if con.execute('SELECT 1 FROM attempts WHERE run_id=?',(run_id,)).fetchone():raise Conflict('这次任务已提交，可以继续另一项任务。',learning_evidence.alternative_action(con,require_session(con,session_id),run['task_id']))
        lesson,task,purpose=TASK_MAP[run['task_id']]
        if run['task_version']!=task['version']:raise Conflict('任务版本已变化，请重新打开。')
        if not response.strip():raise ValueError('请先填写作答。')
        helps=[dict(r) for r in con.execute('SELECT * FROM assistance WHERE run_id=?',(run_id,))]
        assistance='delivered' if any(h['delivery']=='delivered' for h in helps) else 'uncertain' if helps else 'none'
        if task['kind']=='choice':
            if response not in [o['id'] for o in task['options']]:raise ValueError('请选择题目提供的选项。')
            correct=response==task['answer']
            status='correct' if correct else 'incorrect'
            feedback=task['explanation']
        else:
            correct=None
            status='pending_review'
            feedback='作答已保存。请按以下标准对照，当前结果为待复核，不自动记为已掌握。\n'+'\n'.join('• '+c for c in task['criteria'])
        # A repeated exposed task is practice even if no hint was used in this run.
        family=task.get('family_id',task['id'])
        exposed=any(TASK_MAP.get(row['task_id'],({}, {}, ''))[1].get('family_id',row['task_id'])==family
                    for row in con.execute('SELECT task_id FROM attempts WHERE session_id=?',(session_id,)))
        independent=purpose=='review' and assistance=='none' and not exposed and correct is True
        next_reason='可以继续下一单元；延迟保持仍待检查。' if independent else '换一道新题复核当前理解。' if correct else '根据反馈核对材料，再开始一次练习。' if correct is False else '查看分项标准，保留你的原始论证。'
        result={'status':status,'correct':correct,'feedback':feedback,'assistance':assistance,'independent':independent,
                'purpose':purpose,'task_id':task['id'],'task_version':task['version'],'lesson_id':lesson['id'],
                'label':'新题独立完成' if independent else '受助完成' if correct and assistance!='none' else '任务完成' if correct else '待复核' if correct is None else '需要再练习',
                'next_step_reason':next_reason}
        result.update(family_id=family,exposure_group_id=task.get('exposure_group_id'),rule_version='family-evidence-v2')
        card=MISCONCEPTIONS.get((task['id'],response)) if correct is False else None
        if card:result['diagnosis']={'id':card['id'],'label':card['label'],'hint':card['followup_hint'],'remedy_task_id':card['remediation_task_id'],'caveat':'这只是本次选择的可能解释，不是对长期能力的判断。'}
        identifier=new_id('attempt')
        con.execute('INSERT INTO attempts(id,session_id,run_id,task_id,request_id,response,result,created_at,lesson_id,family_id,exposure_group_id,purpose,assistance,independent,correct,misconception_id,remedy_task_id,classification_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (identifier,session_id,run_id,task['id'],request_id,response,encode(result),now(),lesson['id'],family,task.get('exposure_group_id'),purpose,assistance,int(independent),None if correct is None else int(correct),card['id'] if card else None,card['remediation_task_id'] if card else None,'family-evidence-v2'))
        con.execute('UPDATE sessions SET updated_at=? WHERE id=?',(now(),session_id))
        action=learning_evidence.next_action(con,require_session(con,session_id))
        result['next_step']={**action,'text':next_reason}
        con.execute('UPDATE attempts SET result=? WHERE id=?',(encode(result),identifier))
        event(con,session_id,'attempt_submitted',lesson['title']+'：'+result['label'],{'attempt_id':identifier,'task_id':task['id'],'assistance':assistance})
    return {**result,'attempt_id':identifier,'reused':False}


def save_material(title,text,source='手动录入',session_id=None,request_id=None,evidence_kind='authored'):
    identifier=new_id('material')
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        payload=dict(title=title,text=text,source=source,session_id=session_id)
        if evidence_kind not in ('authored','official_doc','self_reported','external_record'):raise ValueError('资料来源类型无效。')
        if evidence_kind!='authored':payload['evidence_kind']=evidence_kind
        reused=retry_resource(con,'material',request_id,payload)
        if reused:return {'id':reused,'reused':True}
        if session_id:require_session(con,session_id)
        con.execute('INSERT INTO materials(id,session_id,title,text,source,created_at,evidence_kind) VALUES(?,?,?,?,?,?,?)',(identifier,session_id,title.strip(),text,source.strip(),now(),evidence_kind))
        event(con,session_id,'material_added','加入资料：'+title.strip(),{'material_id':identifier})
        remember_resource(con,'material',request_id,payload,identifier)
    return {'id':identifier}


def search_materials(session_id,query=''):
    with db() as con:
        session=require_session(con,session_id)
        rows=con.execute('SELECT * FROM materials WHERE archived=0 AND (session_id=? OR session_id IS NULL) ORDER BY created_at DESC',(session_id,)).fetchall()
    tokens=[]
    for token in re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+',query.lower()):
        tokens.append(token)
        if len(token)>3 and re.search(r'[\u3400-\u9fff]',token):
            tokens.extend(token[index:index+2] for index in range(len(token)-1))
    tokens=list(dict.fromkeys(tokens))
    results=[]
    for row in rows:
        item=dict(row)
        if item.get('lesson_id') and LESSON_MAP.get(item['lesson_id'],{}).get('course_id')!=session['course_id']:continue
        paragraphs=[p.strip() for p in re.split(r'\n\s*\n',item['text']) if p.strip()]
        for index,p in enumerate(paragraphs):
            score=sum(t in p.lower() or t in item['title'].lower() for t in tokens)
            if not tokens or score:
                results.append({'material_id':item['id'],'key':'material:'+item['id'],'title':item['title'],'locator':'段落 '+str(index+1),'paragraph':index+1,'text':p[:1400],'score':score})
    return sorted(results,key=lambda x:x['score'],reverse=True)[:6]


def knowledge_graph(session_id):
    """Derive a graph from saved records; never ask an LLM to invent graph facts."""
    with db() as con:
        session=require_session(con,session_id)
        actual_states=states(con,session_id)
        attempts=[dict(r) for r in con.execute('SELECT * FROM attempts WHERE session_id=? ORDER BY created_at DESC',(session_id,))]
        linked_materials=[dict(r) for r in con.execute('SELECT id,title,source FROM materials WHERE session_id=? AND archived=0 ORDER BY created_at',(session_id,))]
        public_count=con.execute('SELECT COUNT(*) FROM materials WHERE session_id IS NULL AND archived=0').fetchone()[0]
    root_id='goal:'+session_id
    nodes=[{'id':root_id,'kind':'goal','title':session['title'],'description':session['goal'],'state_label':'已保存的学习目标','evidence_count':len(attempts),
            'source':{'kind':'learner_goal','record_id':session_id,'label':'当前学习空间中保存的目标'},'lesson_id':None}]
    edges=[]
    def link(source,target,relation,label,provenance):
        edges.append({'id':relation+':'+source+'>'+target,'source':source,'target':target,'relation':relation,'label':label,'provenance':provenance})
    if session['course_id']:
        lessons=[l for l in LESSONS if l['course_id']==session['course_id']]
        previous=None
        for lesson in lessons:
            identifier='objective:'+lesson['id']
            evidence=[a for a in attempts if TASK_MAP.get(a['task_id'],({},))[0].get('id')==lesson['id']]
            origin={'kind':'content_pack','record_id':lesson['id'],'version':1,'label':'知行伴学课程 · '+lesson['title']+' · v1'}
            nodes.append({'id':identifier,'kind':'objective','title':lesson['title'],'description':lesson['objective'],'lesson_id':lesson['id'],
                          'state_label':actual_states[lesson['id']]['label'],'status':actual_states[lesson['id']]['status'],'current':lesson['id']==session['current_lesson'],
                          'evidence_count':len(evidence),'evidence':[{'id':a['id'],'created_at':a['created_at'],'label':attempt_result(a)['label']} for a in evidence[:5]],'source':origin})
            link(root_id,identifier,'contains','课程包含',origin['label'])
            if previous:link(previous,identifier,'course_sequence','课程顺序','当前课程包中的发布顺序；不是自动推断的先修关系')
            previous=identifier
        # Only this local programming pack explicitly declares these prerequisites.
        declared=DECLARED_PREREQUISITES
        available={l['id'] for l in lessons}
        for target,requirements in declared.items():
            if target not in available:continue
            for prerequisite in requirements:
                if prerequisite in available:link('objective:'+prerequisite,'objective:'+target,'declared_prerequisite','课程声明先修','本课程明确编写的先修建议；不是基于学生数据推断或全学科通则')
    else:
        plan=session['plan'] if isinstance(session['plan'],dict) else {}
        active=plan.get('active')
        previous=None
        if active:
            for index,item in enumerate(active['nodes']):
                identifier='plan:'+active['revision']+':'+item['id']
                origin={'kind':'confirmed_plan','record_id':active['revision'],'label':'已确认学习路线 · '+active['revision'][-8:]}
                nodes.append({'id':identifier,'kind':'plan_objective','title':item['title'],'description':item['objective'],'lesson_id':None,
                              'state_label':'路线已确认 · 学习证据待收集','evidence_count':0,'source':origin})
                link(root_id,identifier,'contains','路线包含',origin['label'])
                if previous:link(previous,identifier,'plan_sequence','已确认路线顺序',origin['label']+'；不等于已验证的知识先修关系')
                previous=identifier
    plan=session['plan'] if isinstance(session['plan'],dict) else {}
    return {'session_id':session_id,'title':session['title'],'nodes':nodes,'edges':edges,'linked_materials':linked_materials,
            'public_materials_available':public_count,'draft_available':bool(plan.get('draft')),
            'provenance':'来自已保存目标、发布课程、已确认路线和作答记录。未确认草案不加入图谱；资料关联不自动解释为对知识结论的支持。'}
