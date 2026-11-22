"""Strict loading, hashes and explicit built-in fallback for the authored curriculum."""
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).parent/'resources/contest-pack-v1'
MISCONCEPTIONS={}
PACK_INFO={}
OBJECTIVES={}
SOURCES={}
PRIVATE_KEYS={'answer','hint','explanation','expected','rubric','misconception_by_option','evaluation','may_auto_mark_passed','hidden_tests','solution'}


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def _unique(items,key):
    result={item[key]:item for item in items}
    if len(result)!=len(items):raise ValueError('内容包包含重复标识。')
    return result


def load_pack(root,lesson_ids):
    root=Path(root)
    meta=json.loads((root/'pack.json').read_text(encoding='utf-8'))
    required={'public/tasks.jsonl','public/objectives.jsonl','public/sources.jsonl','public/lessons.jsonl','public/relations.jsonl','public/reading_room_observations.csv','private/assessment_contracts.jsonl','private/misconceptions.jsonl'}
    if not required<=set(meta.get('files',{})):raise ValueError('内容包文件清单不完整。')
    for name in required:
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=meta['files'][name]:raise ValueError('内容包文件校验失败：'+name)
    tasks=_unique(rows(root/'public/tasks.jsonl'),'id');contracts=_unique(rows(root/'private/assessment_contracts.jsonl'),'task_id')
    objectives=_unique(rows(root/'public/objectives.jsonl'),'id');sources=_unique(rows(root/'public/sources.jsonl'),'id')
    lessons=_unique(rows(root/'public/lessons.jsonl'),'id');relations=rows(root/'public/relations.jsonl')
    if set(tasks)!=set(contracts) or len(tasks)!=meta['task_count'] or len(objectives)!=meta['objective_count']:raise ValueError('内容包数量或契约关联不一致。')
    if meta.get('checksum')!=hashlib.sha256((root/'public/tasks.jsonl').read_bytes()).hexdigest():raise ValueError('内容包总校验和不匹配。')
    if set(lessons)!=set(lesson_ids):raise ValueError('讲义与当前课时不匹配。')
    for objective in objectives.values():
        if objective.get('lesson_id') not in lesson_ids:raise ValueError('目标缺少有效课时归属：'+objective['id'])
    for task in tasks.values():
        contract=contracts[task['id']]
        if PRIVATE_KEYS&set(task):raise ValueError('公开题目中含私有判定字段。')
        if task['version']!=contract['version'] or not task.get('family_id') or not task.get('exposure_group_id'):raise ValueError('题目缺少版本或题族。')
        if not task.get('objective_ids') or not set(task['objective_ids'])<=set(objectives):raise ValueError('题目目标无法定位。')
        if not task.get('source_refs') or not set(task['source_refs'])<=set(sources):raise ValueError('题目来源无法定位。')
        if len({objectives[oid]['lesson_id'] for oid in task['objective_ids']})!=1:raise ValueError('题目跨多个课时，需要显式拆分。')
        if task['kind']=='choice':
            options=[o['id'] for o in task['options']]
            if len(set(options))!=len(options) or contract.get('answer') not in options:raise ValueError('选择题判据无效。')
        elif task['kind']=='written':
            if contract.get('evaluation')!='pending_rubric_review' or not contract.get('criteria') or contract.get('may_auto_mark_passed') is True:raise ValueError('开放作答必须保留待复核标准。')
        else:raise ValueError('不支持的题型。')
    cards=_unique(rows(root/'private/misconceptions.jsonl'),'id');index={}
    for card in cards.values():
        tid=card['trigger_task_id'];option=card['trigger_option'];remedy=card['remediation_task_id']
        if tid not in tasks or remedy not in tasks:raise ValueError('错因映射缺少真实任务。')
        if contracts[tid].get('misconception_by_option',{}).get(option)!=card['id']:raise ValueError('错因卡与契约不一致。')
        if option==contracts[tid].get('answer') or option not in {o['id'] for o in tasks[tid].get('options',[])}:raise ValueError('错因不能绑定正确选项。')
        if (tid,option) in index or tasks[remedy]['purpose']!='remediation':raise ValueError('补救映射不明确。')
        index[(tid,option)]=card
    for tid,contract in contracts.items():
        if any((tid,option) not in index for option in contract.get('misconception_by_option',{})):raise ValueError('契约错因没有对应卡片。')
    for edge in relations:
        if edge['source'] not in objectives or edge['target'] not in objectives:raise ValueError('知识关系端点不存在。')
        if edge['type']=='bridge_candidate' and edge.get('may_auto_share_mastery') is not False:raise ValueError('候选桥接不得自动共享掌握。')
    with (root/'public/reading_room_observations.csv').open(encoding='utf-8-sig',newline='') as stream:observations=list(csv.DictReader(stream))
    if not observations or any(not 0<=int(r['occupied_seats'])<=int(r['available_seats']) or r['data_origin']!='authored_demo_not_real_measurement' for r in observations):raise ValueError('演示表范围或来源标识无效。')
    for lesson in lessons.values():
        if not lesson.get('sections') or any(not isinstance(p.get('title'),str) or not isinstance(p.get('text'),str) for p in lesson['sections']):raise ValueError('讲义段落无效。')
    return dict(meta=meta,tasks=tasks,contracts=contracts,objectives=objectives,sources=sources,cards=index,observations=observations,lessons=lessons)


def install(lessons,task_map):
    MISCONCEPTIONS.clear();PACK_INFO.clear();OBJECTIVES.clear();SOURCES.clear()
    lesson_map={l['id']:l for l in lessons}
    try:data=load_pack(ROOT,set(lesson_map))
    except (OSError,ValueError,KeyError,TypeError):
        task_map.clear()
        for lesson in lessons:
            lesson['tasks']=[]
            for purpose in ('practice','review'):
                task={**deepcopy(lesson[purpose]),'purpose':purpose,'lesson_id':lesson['id'],'family_id':lesson['id']+'-existing-family','exposure_group_id':'obj-'+lesson['id']}
                lesson['tasks'].append(task);task_map[task['id']]=(lesson,task,purpose)
        PACK_INFO.update(id='builtin-v1',version='1',task_count=len(task_map),objective_count=len(lessons),sha256='',status='builtin_fallback',warnings=['外部内容包缺失或校验失败，当前使用内置学习任务。'])
        return
    OBJECTIVES.update(data['objectives']);SOURCES.update(data['sources']);MISCONCEPTIONS.update(data['cards'])
    for lesson in lessons:
        lesson['tasks']=[]
        for key in ('title','objective','sections'):lesson[key]=deepcopy(data['lessons'][lesson['id']][key])
    task_map.clear()
    for public in data['tasks'].values():
        contract=data['contracts'][public['id']]
        lesson=lesson_map[OBJECTIVES[public['objective_ids'][0]]['lesson_id']]
        task={**deepcopy(public),**{k:deepcopy(contract[k]) for k in ('answer','hint','explanation','criteria','misconception_by_option') if k in contract},'lesson_id':lesson['id']}
        task.setdefault('hint','先核对题目条件，再解释你的判断。');task.setdefault('explanation','请按公开标准对照，开放作答保持待复核。')
        if public['purpose']=='bridge_demo':task['context_table']={'label':'项目自编演示表，并非真实测量','rows':data['observations']}
        task_map[task['id']]=(lesson,task,task['purpose']);lesson['tasks'].append(task)
        if task['purpose'] in ('practice','review'):lesson[task['purpose']]=task
    meta=data['meta']
    PACK_INFO.update(id=meta['pack_id'],version=meta['version'],task_count=len(task_map),objective_count=len(OBJECTIVES),sha256=meta['checksum'],status='loaded',warnings=[])


def audit():
    return list(PACK_INFO.get('warnings',[]))
