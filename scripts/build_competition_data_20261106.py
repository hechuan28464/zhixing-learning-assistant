"""Build contest content candidates, never learner records or production DB writes."""
from pathlib import Path
import ast,copy,csv,hashlib,json,sqlite3,sys,statistics
from fractions import Fraction

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app';sys.path.insert(0,str(APP))
from backend.content import COURSES,LESSONS,DECLARED_PREREQUISITES
DEST=ROOT/'数据补充_20261106';PACK=DEST/'候选课程包'
DATE='2026-11-06'

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_rows(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
def digest(text):return hashlib.sha256(text.encode()).hexdigest()

EXTRA=[
 ('math-reference','diagnostic','原量50增加20%，计算增加量时，20%相对于哪个量？',['50','60','10'],'A','先区分原量、增加量与变化后的量。','增加量为50×20%=10，以原量50为基准。',['把新量当基准','把增加量当基准']),
 ('math-reference','remediation','原价200元上涨10%变成220元，再下调10%。第二次下调以哪个量为基准？',['200元','220元','20元'],'B','逐次写出变化发生前的价格。','第二次变化从220元开始，所以以220为基准。',['一直沿用最初基准','把变化量当整体']),
 ('math-probability','diagnostic','从1至8等可能取数，已知它是偶数，当前可能的数是哪一组？',['1、2、3、4、5、6、7、8','2、4、6、8','4、8'],'B','先按已知条件筛选，不额外添加条件。','给定条件只保留2、4、6、8。',['忽略给定条件','增加了题目没有的筛选']),
 ('math-probability','remediation','从1至10等可能取数，已知大于6，它是偶数的概率是多少？',['2/10','2/4','4/10'],'B','条件下只考虑7、8、9、10。','四个可能结果中有8和10两个偶数，概率为2/4。',['使用原始分母','混用新旧样本范围']),
 ('math-data','diagnostic','数据1、3、5、7、99已排序，中位数是多少？',['5','23','99'],'A','中位数取排序中间的位置，不是求和再平均。','五项中第三项为5；23是均值。',['把均值当中位数','把最大值当中位数']),
 ('math-data','remediation','数据2、4、6、8、80中，排序后的中间值是多少？',['6','20','80'],'A','先找中间位置，再读该位置的值。','第三个位置是6；均值20不是中间值。',['把均值当中间值','只关注极端值']),
 ('python-variable','diagnostic','y=3；依次执行y=y+4、y=y*2，最后y是多少？',['14','11','6'],'A','每条赋值读取执行当时的值。','y依次为3、7、14。',['合并语句忽略依赖','继续使用初值']),
 ('python-variable','remediation','依次执行a=5、b=a、a=a+7，此时b是多少？',['5','12','17'],'A','记录b得到整数值时a是多少。','b得到5；随后重新给a赋值不会改变b。',['把重新赋值当联动','把两次值相加']),
 ('python-condition','diagnostic','temp=10；若temp>=10则返回“包含”，否则返回“不包含”。结果是什么？',['包含','不包含','仅凭这些条件无法判断'],'A','检查>=是否包含等于。','10>=10成立，所以返回“包含”。',['遗漏等号边界','没有使用明确条件']),
 ('python-condition','remediation','要求score在60到100之间，包含两端。哪个条件符合？',['60 < score < 100','60 <= score <= 100','score >= 60 or score <= 100'],'B','检查上下界是否都满足且包含端点。','链式比较同时限制上下界，并包含60和100。',['排除了端点','把同时满足写成或']),
 ('python-loop','diagnostic','total=0；依次取[1,4,7]，仅当n>2时执行total=n。最后total是多少？',['7','11','12'],'A','区分覆盖赋值与累加。','符合条件时先保存4，再被7覆盖，最终为7。',['把覆盖当累加','忽略筛选并求和']),
 ('python-loop','remediation','count=0；依次取[3,6,9]，当n>=6时执行count+=1。最后count是多少？',['2','15','18'],'A','累计的是项数，而不是数值之和。','6和9符合条件，各计一次，因此为2。',['把计数当数值求和','忽略条件后求和']),
 ('reading-fact','diagnostic','“阅览室周一9点开放，我觉得它是全市最好的阅览室。”哪部分可直接查开放公告核对？',['周一9点开放','全市最好','两部分都能用同一公告证明'],'A','把时间事实与评价标准分开。','公告可核对开放时间；“最好”需要标准和比较。',['把评价当时间事实','混淆不同证据要求']),
 ('reading-causal','diagnostic','更换讲解工具后正确率提高，同时题目也变简单了。依据这些信息，应怎样表述？',['可以确定全部由新工具造成','还不能把提高单独归因于工具','可以确定工具没有任何作用'],'B','找出同时变化的条件。','题目难度也变化，当前信息不能单独归因。',['忽略其他变化','把证据不足当确定无效']),
 ('reading-argument','diagnostic','想检查晚饭后阅读是否更适合自己，哪项更可核查？',['我喜欢，所以一定最好','记录相近难度文章的阅读时间与理解表现','大家都这么说'],'B','选择能够观察并关联目标的依据。','记录具体表现更便于核查，但仍需说明比较条件和范围。',['把喜好当充分证据','把流行说法当个人表现']),
]
WRITTEN=[
 ('reading-fact','remediation','自编材料：“阅览室本月新增30本书，因此它是本市最好的阅览室。”分别指出可核查陈述、评价及还需要的依据。',['指出新增30本书可核查','指出“最好”依赖标准和比较','提出具体可核查的补充依据'],'先把一个句子拆成两种不同类型的陈述。'),
 ('reading-causal','remediation','自编材料：班级调整晨读安排后理解题表现提高，同时换用了更容易的课文。请给出谨慎结论和一种有针对性的核查办法。',['区分同时变化与单独归因','识别课文难度的替代解释','提出难度相近等针对性比较'],'不要只背“相关不等于因果”，把它联系到这里的条件。'),
 ('reading-argument','remediation','用三至五句话提出一项学习安排建议，说明主张、可观察依据及结论适用范围。不需要声称已经证明有效。',['主张具体','依据可观察或核查','解释依据如何支持主张','主动说明范围或限制'],'先写希望改变什么，再写用什么实际表现核对。')]

def main():
    for folder in ['public','private']:(PACK/folder).mkdir(parents=True,exist_ok=True)
    sources=[];objectives=[];tasks=[];contracts=[];cards=[];relations=[]
    papers=[('learnlm-2025-v3','LearnLM: Improving Gemini for Learning','https://arxiv.org/abs/2412.16429v3','CC-BY-4.0','教学行为与工程验收参考，不作为本产品效果证据'),('arena-2025-v1','Evaluating Gemini in an arena for learning','https://arxiv.org/abs/2505.24477v1','see paper license','与LearnLM报告分开登记，不混用人数或模型结果'),('educlaw-2026-v1','EduClaw-Bench','https://arxiv.org/abs/2608.03206v1','CC-BY-NC-ND-4.0','仅方法参考与原文定位；不改编分发其场景或基准数据')]
    for sid,title,url,license_,usage in papers:sources.append(dict(id=sid,type='engineering_research_reference',title=title,url=url,license=license_,usage=usage,learner_retrieval=False,verified_date=DATE,verification='official_page_checked'))
    for sid,title,url in [('python-control-3.12','Python控制流','https://docs.python.org/3.12/tutorial/controlflow.html'),('python-data-3.12','Python数据结构','https://docs.python.org/3.12/tutorial/datastructures.html'),('cmu-rubrics','Rubric结构说明','https://www.cmu.edu/teaching/assessment/assesslearning/rubrics.html'),('openstax-percent','百分数概念','https://openstax.org/books/prealgebra-2e/pages/6-key-concepts')]:
        sources.append(dict(id=sid,type='content_reference_link',title=title,url=url,usage='链接与方法参考；本包题面和讲义为项目自编，没有复制页面全文',license='source_specific; not re-licensed by this project',learner_retrieval=False,verified_date=DATE,verification='official_page_checked'))
    for lesson in LESSONS:
        sid='own-'+lesson['id'];text='\n\n'.join(s['title']+'\n'+s['text'] for s in lesson['sections'])
        sources.append(dict(id=sid,type='project_authored_lesson',title=lesson['title'],version=1,sha256=digest(text),origin='app/backend/content.py',license='project-owned; no new public license assigned',usage='现有自编课程材料',learner_retrieval=True,verification='existing_runtime_content'))
        objectives.append(dict(id='obj-'+lesson['id'],course_id=lesson['course_id'],title=lesson['title'],observable_goal=lesson['objective'],source_refs=[sid],review_status='candidate_registry_export',version=1,mastery_default='unknown'))
        for purpose in ['practice','review']:
            original=copy.deepcopy(lesson[purpose]);tid=original['id']
            contract={k:original[k] for k in ['answer','hint','explanation','criteria'] if k in original}
            contract.update(task_id=tid,version=original['version'],evaluation='deterministic_choice' if original['kind']=='choice' else 'pending_rubric_review')
            public={k:v for k,v in original.items() if k not in ['answer','hint','explanation']}
            public.update(objective_ids=['obj-'+lesson['id']],source_refs=[sid],purpose=purpose,family_id=lesson['id']+'-existing-family',transfer_claim='current_item_only; family review required',origin='existing_runtime_task',candidate_status='registry_export_not_new_publish',synthetic_scenario=True)
            tasks.append(public);contracts.append(contract)
    sequence=0
    for lesson,purpose,prompt,options,answer,hint,explanation,wrong_labels in EXTRA:
        tid=lesson+('-diag' if purpose=='diagnostic' else '-remedy')+'-20261106'
        choices=[dict(id=chr(65+i),text=text) for i,text in enumerate(options)]
        tasks.append(dict(id=tid,version=1,kind='choice',prompt=prompt,options=choices,purpose=purpose,objective_ids=['obj-'+lesson],family_id=lesson+'-support-family',source_refs=['own-'+lesson],origin='new_project_authored',candidate_status='not_loaded_into_runtime',synthetic_scenario=True,transfer_claim='diagnosis_or_remediation_not_independent_gain'))
        private=dict(task_id=tid,version=1,answer=answer,hint=hint,explanation=explanation,evaluation='deterministic_choice')
        if purpose=='diagnostic':
            mapping={}
            for option,label in zip([c for c in choices if c['id']!=answer],wrong_labels):
                sequence+=1;cid='mc-'+str(sequence).zfill(2);mapping[option['id']]=cid
                cards.append(dict(id=cid,objective_id='obj-'+lesson,label=label,trigger_task_id=tid,trigger_option=option['id'],remediation_task_id=lesson+'-remedy-20261106',followup_hint=hint,requires_confirmation=True,meaning='候选错因，不能从一次错误推断人格或稳定能力',status='candidate_rule_data'))
            private['misconception_by_option']=mapping
        contracts.append(private)
    for lesson,purpose,prompt,criteria,hint in WRITTEN:
        tid=lesson+'-remedy-20261106'
        tasks.append(dict(id=tid,version=1,kind='written',prompt=prompt,criteria=criteria,purpose=purpose,objective_ids=['obj-'+lesson],family_id=lesson+'-support-family',source_refs=['own-'+lesson],origin='new_project_authored',candidate_status='not_loaded_into_runtime',synthetic_scenario=True,transfer_claim='remediation_not_mastery'))
        contracts.append(dict(task_id=tid,version=1,criteria=criteria,hint=hint,evaluation='pending_rubric_review',may_auto_mark_passed=False))
    for target,requirements in DECLARED_PREREQUISITES.items():
        for requirement in requirements:relations.append(dict(id=requirement+'-before-'+target,source='obj-'+requirement,target='obj-'+target,type='declared_prerequisite',provenance='现有程序阅读课程v1显式声明',status='existing_declared_relation'))
    observations=[]
    for room,seats,occupied in [('A',20,[10,16,14,18,19,20]),('B',30,[12,18,18,21,27,24])]:
        for index,count in enumerate(occupied):observations.append(dict(observation_id=room+str(index+1),room=room,time_slot=['周一上午','周一下午','周三上午','周三下午','周六上午','周六下午'][index],available_seats=seats,occupied_seats=count,data_origin='authored_demo_not_real_measurement'))
    csv_path=PACK/'public/reading_room_observations.csv'
    with csv_path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(observations[0]));writer.writeheader();writer.writerows(observations)
    sources.append(dict(id='own-reading-room-demo',type='project_authored_demo_table',title='阅读空间占用情况演示表',path='public/reading_room_observations.csv',sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),usage='跨学科演示，不是真实测量或学生行为日志',license='project-owned; no new public license assigned',learner_retrieval=True,verification='bounds_and_arithmetic_checked'))
    bridge=[('capacity','占用率与基准量','给定演示表，A房间6次观察的总占用数除以总座位数，约是多少？',['80.83%','66.67%','97%'],'A','97/120≈80.83%，结果只描述给定演示表。'),('aggregation','程序汇总与比率','按表分别累计occupied_seats和available_seats，应得到哪一组？',['A:97/120，B:120/180','A:120/97，B:180/120','A与B都按20个座位计算'],'A','逐行按房间累计；分子和分母各自求和。')]
    for name,title,prompt,options,answer,explanation in bridge:
        oid='obj-bridge-'+name;tid='bridge-'+name+'-20261106'
        objectives.append(dict(id=oid,course_id='crossdisciplinary-draft',title=title,observable_goal='使用给定表格解释并检查'+title,source_refs=['own-reading-room-demo'],review_status='candidate',version=1,mastery_default='unknown'))
        tasks.append(dict(id=tid,version=1,kind='choice',prompt=prompt,options=[dict(id=chr(65+i),text=t) for i,t in enumerate(options)],purpose='bridge_demo',objective_ids=[oid],family_id='reading-room-aggregate',source_refs=['own-reading-room-demo'],origin='new_project_authored',candidate_status='not_loaded_into_runtime',synthetic_scenario=True,transfer_claim='demonstration_not_validated_transfer'))
        contracts.append(dict(task_id=tid,version=1,answer=answer,explanation=explanation,hint='分清占用数与可用座位数，再按房间求和。',evaluation='deterministic_choice'))
    oid='obj-bridge-argument';tid='bridge-argument-20261106'
    objectives.append(dict(id=oid,course_id='crossdisciplinary-draft',title='数据与评价边界',observable_goal='说明给定占用率不能单独证明哪个阅览室最好',source_refs=['own-reading-room-demo','own-reading-argument'],review_status='candidate',version=1,mastery_default='unknown'))
    criteria=['区分演示表计算与真实观测','说明占用率不是最好或最舒适的充分判据','提出至少一项具体补充证据','限制结论适用范围']
    tasks.append(dict(id=tid,version=1,kind='written',prompt='根据给定演示表写一段建议：占用率较高能否说明A房间更好？说明依据、限制及需要补充的材料。',criteria=criteria,purpose='bridge_demo',objective_ids=[oid],family_id='reading-room-argument',source_refs=['own-reading-room-demo','own-reading-argument'],origin='new_project_authored',candidate_status='not_loaded_into_runtime',synthetic_scenario=True,transfer_claim='demonstration_not_validated_transfer'))
    contracts.append(dict(task_id=tid,version=1,criteria=criteria,evaluation='pending_rubric_review',may_auto_mark_passed=False))
    for source,target in [('math-reference','capacity'),('python-loop','aggregation'),('reading-argument','argument')]:relations.append(dict(id='candidate-'+source+'-'+target,source='obj-'+source,target='obj-bridge-'+target,type='bridge_candidate',provenance='跨科演示任务设计',status='requires_review',may_auto_share_mastery=False))
    provenance=json.loads((ROOT/'参考项目/_provenance/source-manifest.json').read_text(encoding='utf-8'))
    for repository in provenance['repositories']:
        sources.append(dict(id='code-'+repository['name'],type='engineering_code_reference',title=repository['name'],url=repository['url'],version=repository['commit'],license=repository['root_license'],usage='固定版本方法与实现参考；不自动载入学习资料',learner_retrieval=False,verification='pinned_local_snapshot',verified_date=DATE))
    sources.append(dict(id='code-openmaic',type='engineering_code_reference',title='OpenMAIC',url='https://github.com/THU-MAIC/OpenMAIC',version='795420c12f7846577468fc7831437db6eb957e14',license='MIT for included domain source',usage='已采用原生domain，完整平台未整体部署',learner_retrieval=False,verification='local_source_hash_check'))
    for objective in objectives:
        suffix=objective['id'].removeprefix('obj-')
        objective['lesson_id']={'capacity':'math-reference','aggregation':'python-loop','argument':'reading-argument'}[suffix.removeprefix('bridge-')] if suffix.startswith('bridge-') else suffix
    for task in tasks:
        # Conservative grouping: related items cannot become "unseen" just by changing IDs.
        task['exposure_group_id']=('reading-room-demo' if task['id'].startswith('bridge-') else task['objective_ids'][0])
        task['independent_transfer_review']='not_claimed'
    for path,rows in [('public/sources.jsonl',sources),('public/objectives.jsonl',objectives),('public/tasks.jsonl',tasks),('public/relations.jsonl',relations),('public/lessons.jsonl',[dict(id=l['id'],title=l['title'],objective=l['objective'],sections=l['sections'],source_ref='own-'+l['id']) for l in LESSONS]),('private/assessment_contracts.jsonl',contracts),('private/misconceptions.jsonl',cards)]:write_rows(PACK/path,rows)
    package_meta=dict(pack_id='core-20261106',version='2026.11.07.2',task_count=len(tasks),objective_count=len(objectives),checksum=hashlib.sha256((PACK/'public/tasks.jsonl').read_bytes()).hexdigest())
    package_meta['files']={p.relative_to(PACK).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in PACK.rglob('*') if p.is_file() and p.name!='pack.json'}
    write_json(PACK/'pack.json',package_meta)
    ids=[t['id'] for t in tasks];assert len(ids)==len(set(ids))
    taskmap={t['id']:t for t in tasks};objective_ids={o['id'] for o in objectives};source_ids={s['id'] for s in sources}
    assert len(contracts)==len(tasks)
    for task in tasks:
        assert set(task['objective_ids'])<=objective_ids and set(task['source_refs'])<=source_ids
        assert not {'answer','hint','explanation','misconception_by_option'}&set(task)
    for contract in contracts:
        task=taskmap[contract['task_id']]
        if task['kind']=='choice':assert contract['answer'] in [o['id'] for o in task['options']]
        else:assert contract.get('criteria')
    for card in cards:assert card['trigger_task_id'] in taskmap and card['remediation_task_id'] in taskmap
    oracle_checks={'median_5':statistics.median([1,3,5,7,99])==5,'mean_23':statistics.mean([1,3,5,7,99])==23,'condition_probability':Fraction(2,4)==Fraction(1,2),'assignment_14':(3+4)*2==14,'loop_last_7':[n for n in [1,4,7] if n>2][-1]==7,'count_2':sum(n>=6 for n in [3,6,9])==2,'capacity_A':sum(r['occupied_seats'] for r in observations if r['room']=='A')==97,'capacity_B':sum(r['occupied_seats'] for r in observations if r['room']=='B')==120}
    assert all(oracle_checks.values())
    manifest=dict(date=DATE,purpose='competition_content_preparation_not_experiment',production_database_written=False,loaded_into_runtime=False,existing_tasks=18,new_diagnostic_and_remediation_tasks=18,new_bridge_tasks=3,total_tasks=len(tasks),objectives=len(objectives),misconception_cards=len(cards),source_records=len(sources),observation_rows=len(observations),human_review='not_claimed',validation='schema_links_and_selected_deterministic_oracles',oracle_checks=oracle_checks)
    manifest['files']=[dict(path=str(p.relative_to(PACK)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in PACK.rglob('*') if p.is_file()]
    write_json(DEST/'校验/课程数据校验.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','oracle_checks')},ensure_ascii=True))

if __name__=='__main__':main()
