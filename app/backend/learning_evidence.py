"""Small deterministic projections for actual task records, never inferred learner scores."""
from .content import LESSONS, TASK_MAP
from .pack_registry import OBJECTIVES
from .store import attempt_result
from datetime import datetime,timedelta,timezone

REVIEW_INTERVALS=(1,3,7)


def review_due(attempts):
    if not attempts:return None
    try:
        timestamp=datetime.fromisoformat(attempts[-1]['created_at'].replace('Z','+00:00'))
        if timestamp.tzinfo is None:timestamp=timestamp.replace(tzinfo=timezone.utc)
        return (timestamp+timedelta(days=REVIEW_INTERVALS[min(len(attempts)-1,len(REVIEW_INTERVALS)-1)])).isoformat()
    except (ValueError,TypeError):return None


def results_for(con, session_id, lesson_id):
    return [dict(row) | {'result': attempt_result(row)} for row in con.execute(
        'SELECT * FROM attempts WHERE session_id=? ORDER BY created_at,rowid', (session_id,))
        if (dict(row).get('lesson_id') or TASK_MAP.get(row['task_id'], ({},))[0].get('id')) == lesson_id]


def lesson_objectives(lesson_id, attempts):
    """Objectives this lesson is responsible for; falls back to the tasks actually attempted."""
    if lesson_id:
        declared = [oid for oid, objective in OBJECTIVES.items() if objective.get('lesson_id') == lesson_id]
        if declared:return declared
    seen = []
    for attempt in attempts:
        task = TASK_MAP.get(attempt.get('task_id'), ({}, None))[1] or {}
        for objective_id in task.get('objective_ids') or []:
            if objective_id not in seen:seen.append(objective_id)
    return seen


def coverage_dimension(attempts, lesson_id):
    """Coverage counts lesson objectives backed by independent evidence, never raw attempt volume."""
    objectives = lesson_objectives(lesson_id, attempts)
    covered = {}
    for attempt in attempts:
        result = attempt['result']
        if not (result.get('independent') and result.get('correct') is True):continue
        task = TASK_MAP.get(attempt.get('task_id'), ({}, None))[1] or {}
        for objective_id in task.get('objective_ids') or []:
            if objective_id in objectives and objective_id not in covered:covered[objective_id] = attempt['id']
    total, hit = len(objectives), len(covered)
    scope = {'total': total, 'covered': hit}
    if not attempts:
        return {'value': 'none', 'label': '尚未观察', 'basis': '从一道短诊断开始', 'attempt_ids': [], 'objectives': scope}
    if not total:
        return {'value': 'unknown', 'label': '目标尚未定位', 'basis': '本单元没有可核对的 objective_ids', 'attempt_ids': [], 'objectives': scope}
    if hit == total:
        value, label = 'covered', '目标'+str(hit)+'/'+str(total)+'有独立证据'
        basis = '本单元目标均已有独立作答佐证，不代表全部课程'
    elif hit:
        value, label = 'partial', '目标'+str(hit)+'/'+str(total)+'有独立证据'
        basis = '按本单元 objective_ids 与独立作答比对，共 '+str(len(attempts))+' 次作答'
    else:
        value, label = 'observed', '目标0/'+str(total)+'有独立证据'
        basis = '已有 '+str(len(attempts))+' 次作答，但还没有符合独立条件的证据'
    return {'value': value, 'label': label, 'basis': basis, 'attempt_ids': list(covered.values()), 'objectives': scope}


def dimensions(attempts,at=None,lesson_id=None):
    results = [a['result'] for a in attempts]
    independent = [a for a in attempts if a['result'].get('independent') and a['result'].get('correct') is True]
    helps = [r.get('assistance', 'uncertain') for r in results]
    help_value = 'delivered' if 'delivered' in helps else 'uncertain' if 'uncertain' in helps else 'none' if helps else 'unknown'
    due=review_due(independent)
    due_now=bool(due and (at or datetime.now(timezone.utc))>=datetime.fromisoformat(due))
    basis='已到建议回看时间，保持情况仍未检查' if due_now else '已安排后续回看，保持情况尚未检查' if due else '尚无间隔后的独立复核证据'
    ids=[a['id'] for a in attempts]
    return {
        'independent': {'value': bool(independent), 'label': '有当前题族独立表现' if independent else '尚无独立新题记录',
                        'basis': '依据未记录帮助且首次接触该题族的复核作答' if independent else '尚无符合独立复核条件的作答',
                        'attempt_ids': [a['id'] for a in independent]},
        'help': {'value': help_value, 'label': {'delivered':'有提示或导师帮助','uncertain':'帮助送达尚未确认','none':'本单元未记录提示','unknown':'尚无帮助条件记录'}[help_value],
                 'basis': '按提交前的帮助记录核对' if helps else '还没有提交作答','attempt_ids':ids},
        'coverage': coverage_dimension(attempts, lesson_id),
        'retention': {'status':'due' if due_now else 'not_checked','label':'建议回看' if due_now else '未检查','basis':basis,'reason':basis,'due':due,'attempt_ids':[a['id'] for a in independent[-1:]]},
    }


def next_action(con, session):
    lesson = next((l for l in LESSONS if l['id'] == session.get('current_lesson') and l['course_id'] == session.get('course_id')), None)
    if not lesson:
        return {'kind': 'route', 'task_id': None, 'lesson_id': None, 'title': '回到学习目标和路线', 'reason': '先确认想解决的问题，并加入相关资料。'}
    tasks = lesson.get('tasks', []); observed = results_for(con, session['id'], lesson['id'])
    by_purpose = {purpose: next((t for t in tasks if t['purpose'] == purpose), None) for purpose in ('diagnostic','practice','review','remediation','bridge_demo')}
    def action(kind, task, title, reason):
        return {'kind': kind, 'task_id': task['id'] if task else None, 'lesson_id': task.get('lesson_id',lesson['id']) if task else lesson['id'],
                'title': title, 'reason': reason, 'purpose': task['purpose'] if task else None, 'policy_version': 'evidence-v1',
                'evidence_refs': [a['id'] for a in observed[-1:]],
                'alternatives': [{'task_id': t['id'], 'purpose': t['purpose']} for t in tasks if t != task]}
    if not observed:
        return action('diagnostic', by_purpose['diagnostic'] or by_purpose['practice'], '先看看从哪里开始', '当前单元还没有作答记录，先用一道短诊断确认起点。')
    last = observed[-1]['result']; diagnosis = last.get('diagnosis')
    if diagnosis and diagnosis.get('remedy_task_id') in TASK_MAP:
        return action('remedy', TASK_MAP[diagnosis['remedy_task_id']][1], '补上这一小步', '这次选择可能与「'+diagnosis['label']+'」有关，可以先做对应补救。')
    if last.get('correct') is None:
        return action('wait_review', None, '回看作答标准与自己的依据', '开放作答已保存，当前保持待复核，不自动认证掌握。')
    if any(a['result'].get('independent') and a['result'].get('correct') is True for a in observed):
        course=[l for l in LESSONS if l['course_id']==session['course_id']]
        index=next(i for i,l in enumerate(course) if l['id']==lesson['id'])
        if index+1<len(course):
            following=course[index+1]
            task=next((t for t in following['tasks'] if t['purpose']=='diagnostic'),following['practice'])
            return action('advance',task,'进入下一单元：'+following['title'],'本单元已有一次符合题族与帮助条件的复核表现；长期保持仍需后续检查。')
    seen = {a['task_id'] for a in observed}
    if last.get('purpose')=='diagnostic' and last.get('correct') is True and by_purpose['review'] and by_purpose['review']['id'] not in seen:
        return action('review',by_purpose['review'],'直接换题复核，或按需练习','本次诊断已答对，可尝试另一题族的复核；是否独立仍核对首次暴露与帮助记录。')
    if last.get('correct') is True and last.get('assistance')!='none' and by_purpose['review'] and by_purpose['review']['id'] not in seen:
        return action('review', by_purpose['review'], '换一道题，检查当前理解', '刚才的完成包含帮助；这次复核仍会按题族暴露和当前帮助记录判断。')
    candidate = next((by_purpose[p] for p in ('practice','review','bridge_demo') if by_purpose[p] and by_purpose[p]['id'] not in seen), None)
    if candidate:
        return action('practice', candidate, '换一道题，继续检查理解', '依据最近作答选择下一项任务；是否独立仍按题族和帮助条件核对。')
    return action('practice', by_purpose['practice'], '回看反馈，再练一遍', '本单元已有作答记录；重复练习会保留暴露条件，不当作新题独立表现。')


def alternative_action(con,session,task_id):
    proposed=next_action(con,session)
    if proposed.get('task_id') and proposed['task_id']!=task_id:return proposed
    entry=TASK_MAP.get(task_id)
    if entry:
        task=next((t for t in sorted(entry[0]['tasks'],key=lambda t:({'review':0,'practice':1}.get(t['purpose'],2))) if t['id']!=task_id),None)
        if task:return {'kind':'practice','task_id':task['id'],'lesson_id':entry[0]['id'],'title':'打开另一项任务','reason':'原作答已保存；另一任务的独立性仍按题族和帮助条件核对。',
                        'purpose':task.get('purpose'),'policy_version':'evidence-v1','evidence_refs':[],
                        'alternatives':[{'task_id':t['id'],'purpose':t.get('purpose')} for t in entry[0]['tasks'] if t['id']!=task['id']]}
    return proposed


def evidence(con, session):
    lessons = {}
    for lesson in LESSONS:
        if lesson['course_id'] != session.get('course_id'):continue
        attempts = results_for(con, session['id'], lesson['id'])
        lessons[lesson['id']] = {'dimensions': dimensions(attempts, lesson_id=lesson['id']), 'attempts': [
            {'id': a['id'], 'task_id': a['task_id'], 'created_at': a['created_at'], **a['result']} for a in attempts]}
    return {'lessons': lessons, 'unchecked': ['retention'], 'note': '未检查不等于未掌握。'}
