"""Original demonstration learning packs. Private answer contracts stay server-side."""
from copy import deepcopy


def choice(identifier, prompt, options, answer, hint, explanation):
    return {'id': identifier, 'version': 1, 'kind': 'choice', 'prompt': prompt,
            'options': [{'id': chr(65+i), 'text': text} for i, text in enumerate(options)],
            'answer': answer, 'hint': hint, 'explanation': explanation}


def written(identifier, prompt, criteria, hint):
    return {'id': identifier, 'version': 1, 'kind': 'written', 'prompt': prompt,
            'criteria': criteria, 'hint': hint,
            'explanation': '按公开标准逐项对照；开放题保留原始作答，当前版本不自动认证掌握。'}


COURSES = [
    {'id': 'mathematics', 'tag': '数学思维', 'title': '从问题到模型：用数学看见真实世界',
     'subtitle': '比例、概率与数据，让判断多一点依据', 'tint': 'apricot', 'minutes': 45,
     'description': '从日常判断出发，理解百分比、概率和数据背后的条件。', 'level': '基础友好'},
    {'id': 'programming', 'tag': '编程与智能', 'title': 'Python 与真实问题：从小问题开始动手',
     'subtitle': '变量、条件与循环，读懂程序如何工作', 'tint': 'lavender', 'minutes': 45,
     'description': '先预测，再验证思路。当前任务为代码阅读与结果预测，不运行用户代码。', 'level': '零基础可学'},
    {'id': 'reading', 'tag': '阅读与思考', 'title': '在阅读中建立更清晰的思考力',
     'subtitle': '辨别事实、核对证据、组织自己的观点', 'tint': 'rose', 'minutes': 45,
     'description': '用短材料练习解释、质疑和表达，开放作答按标准对照。', 'level': '通识入门'},
]

LESSONS = [
 {'id':'math-reference','course_id':'mathematics','title':'百分比的基准量','objective':'能指出每次变化的基准量，解释连续百分比变化。','minutes':15,
  'sections':[
   {'title':'每个百分比，都有一个“相对于谁”','text':'百分比描述部分与整体的关系。计算变化后的量时，先写出基准量，再用“基准量 ×（1 ± 变化比例）”。两次变化的基准量可能不同，因此不能总把增减比例直接抵消。'},
   {'title':'把变化拆开看','text':'例如一件物品从80元上涨25%，新价格为100元；再从100元下调25%，价格为75元。第二次百分比的基准已经变成100元。画两行计算过程，比记住一个结论更可靠。'},
   {'title':'试着检查你的解释','text':'解释时说清三件事：原量是多少、变化相对于哪个量、最后得到的量是什么。数值正确但基准不清，还值得再核对一次。'}],
  'practice':choice('math-reference-p','原价100元上涨20%，再按新价格下调20%，最终价格是多少？',['100元','96元','80元'],'B','分别写出第一次变化后的价格，以及第二次下调所依据的价格。','第一次为120元；第二次为120×0.8=96元。两个20%的基准不同。'),
  'review':choice('math-reference-r','一本书打八折后售价64元，原价是多少？',['80元','76.8元','51.2元'],'A','把原价设为x，折后价格对应原价的80%。','原价×0.8=64，因此原价为80元。这是同知识点新题，不代表长期保持已验证。')},
 {'id':'math-probability','course_id':'mathematics','title':'概率，需要看条件','objective':'区分总体概率和给定条件后的概率。','minutes':15,
  'sections':[
   {'title':'先确定样本范围','text':'概率的分母来自当前允许考虑的全部情况。加入一个条件后，样本范围可能缩小，因此概率也可能改变。'},
   {'title':'用小集合代替凭感觉','text':'袋中有2个红球和3个蓝球，随机取1个，红球概率为2/5。若已知取出的球来自另一个只装红球的小袋，样本范围已经不同，不能继续沿用2/5。'},
   {'title':'独立与互斥不是同一件事','text':'互斥表示两个事件不能同时发生；独立表示一个事件的发生不改变另一个的概率。不要因为两件事名称不同，就认为彼此独立。'}],
  'practice':choice('math-probability-p','从1至6等可能取一个整数，已知它是偶数，它大于3的概率是多少？',['1/2','2/3','1/3'],'B','条件把可选数缩小为2、4、6，再找其中大于3的数。','条件下只有2、4、6三种等可能结果，其中4和6满足要求，概率为2/3。'),
  'review':choice('math-probability-r','从1至8等可能取一个整数，已知它大于4，它是偶数的概率是多少？',['1/4','3/4','1/2'],'C','先列出给定条件下仍可能出现的数。','条件下为5、6、7、8，其中6、8为偶数，因此为2/4=1/2。')},
 {'id':'math-data','course_id':'mathematics','title':'平均数之外，还有什么','objective':'能根据异常值的影响，解释均值与中位数的差别。','minutes':15,
  'sections':[
   {'title':'一个数字不能讲完全部故事','text':'均值将所有数相加后除以数量；中位数来自排序后居中的位置。二者回答的问题不同，使用前要看数据分布和目的。'},
   {'title':'异常值会怎样影响结果','text':'数据2、3、4、5、36的均值为10，中位数为4。较大的36明显拉高均值，但对中间位置的影响有限。解释“典型情况”时，应说明采用哪个指标以及为什么。'},
   {'title':'保留数据语境','text':'比较群体时还要看样本量、采集方式和单位。某个平均值较高，不自动说明所有成员都更高，也不能直接推出因果。'}],
  'practice':choice('math-data-p','数据1、2、3、4、40的中位数是多少？',['3','10','4'],'A','先排序，再找五个数中间的位置。','五个数已排序，中间的第三个数为3。均值是10，但不是中位数。'),
  'review':choice('math-data-r','将数据2、3、4、5、6中的6换为100，以下哪项正确？',['均值和中位数都不变','均值变大，中位数不变','均值不变，中位数变大'],'B','分别检查总和和排序后第三个位置。','均值受总和变化影响而增大；第三个位置仍为4，因此中位数不变。')},
 {'id':'python-variable','course_id':'programming','title':'变量如何一步步变化','objective':'能按顺序追踪赋值后的变量值。','minutes':15,
  'sections':[
   {'title':'赋值是更新当前值','text':'在Python中，x = x + 2表示先读取右侧的当前x，计算后再存回左侧。它不是代数中要求左右永远相等的方程。'},
   {'title':'给每一步留一个位置','text':'例如x先为3，再执行x = x + 2，此时x为5。可以画“执行前—语句—执行后”的小表，一行只追踪一步。'},
   {'title':'先预测，再读后续','text':'遇到程序先写下预测，逐行检查。当前学习任务只检查程序阅读与结果预测，不会在本机运行你输入的代码。'}],
  'practice':choice('python-variable-p','x = 2\nx = x + 3\nx = x * 2\n最后x是多少？',['7','10','4'],'B','不要把两条更新合并猜测，依次写出x的值。','x依次为2、5、10。'),
  'review':choice('python-variable-r','a = 4\nb = a\na = 9\n此时b是多少？',['9','13','4'],'C','b = a发生时，a的当前整数值是什么？','b得到赋值时的整数值4；之后重新给a赋值不会把b改成9。')},
 {'id':'python-condition','course_id':'programming','title':'条件分支与边界','objective':'能根据条件和边界值判断程序分支。','minutes':15,
  'sections':[
   {'title':'分支取决于条件真假','text':'if后面的条件为真时执行对应语句，否则检查后续分支。比较符号中的等号决定边界值是否被包含。'},
   {'title':'用三个值检查边界','text':'条件是score >= 60时，分别检查59、60、61。这样能发现把>=写成>导致的问题，而不只测试一个普通值。'},
   {'title':'先说规则，再写条件','text':'把“达到60分”翻译为包含60，把“超过60分”翻译为不包含60。任务语言与代码必须一致。'}],
  'practice':choice('python-condition-p','score = 60\nif score > 60:\n    result = "通过"\nelse:\n    result = "再试一次"\nresult是什么？',['通过','再试一次','程序一定报错'],'B','大于号是否包含恰好等于60？','60 > 60为假，因此进入else。这里只是结果预测，未执行代码。'),
  'review':choice('python-condition-r','需求是“年龄在18至25岁之间，包含两端”。哪个条件正确？',['18 < age < 25','age >= 18 or age <= 25','18 <= age <= 25'],'C','两个边界都要满足，并且都包含等号。','链式比较18 <= age <= 25同时限制上下界并包含两端。')},
 {'id':'python-loop','course_id':'programming','title':'循环中的累加与筛选','objective':'区分累加、覆盖赋值和计数。','minutes':15,
  'sections':[
   {'title':'每次循环都要保留什么','text':'total += value会在旧值上累加；total = value会覆盖旧值。count += 1统计数量，total += value统计数值之和。'},
   {'title':'先筛选，再更新','text':'对[2,5,8]只累加大于4的数，需要先判断条件，再把符合的5、8加到累计值中。画出每次是否进入条件、累计值如何变化。'},
   {'title':'别只用一个样例','text':'读懂算法还要考虑空输入、全不符合和恰好位于边界。预测题验证当前理解，真实代码执行需要另外的隔离运行环境。'}],
  'practice':choice('python-loop-p','total = 0\nfor value in [2, 5, 8]:\n    if value > 4:\n        total = value\n最后total是多少？',['13','15','8'],'C','注意更新语句是覆盖赋值，还是累加？','符合条件时total先变成5，再被8覆盖，最后为8。'),
  'review':choice('python-loop-r','count = 0\nfor value in [3, 6, 9]:\n    if value >= 6:\n        count += 1\n最后count是多少？',['2','15','3'],'A','统计的是符合条件的项数，不是这些值的和。','6和9符合条件，各加1，因此count为2。')},
 {'id':'reading-fact','course_id':'reading','title':'区分事实与判断','objective':'能区分可核查陈述与评价性判断。','minutes':15,
  'sections':[
   {'title':'先问这句话如何核查','text':'“图书馆周日开放到18点”可以查阅开放公告；“这是最好的图书馆”包含评价标准。两者都能进入讨论，但不能用相同方式证明。'},
   {'title':'观点也需要条件','text':'评价不必被禁止，但要说明标准。例如“更适合安静阅读”需要观察噪声、座位和开放时间，而不只是喜欢或不喜欢。'},
   {'title':'保留原话与来源','text':'引用材料时区分原文、转述和自己的推断。没有来源时说明未核实，不把语言流畅当成事实可靠。'}],
  'practice':written('reading-fact-p','材料：“社区阅读室本月新增了20个座位，因此它是全市最好的阅读室。”请区分其中的事实陈述与评价，并说明还缺什么依据。',['指出新增20个座位是可核查陈述','指出“全市最好”依赖评价标准与比较','说明至少一种需要补充的依据'],'分别问：哪句话能查记录？哪句话需要先确定评价标准？'),
  'review':written('reading-fact-r','“这门课提供了三次练习，所以所有学生都一定能学会。”请说明观察与推断的边界。',['区分练习次数与学习结果','指出“所有人一定学会”证据不足','提出可以观察的学习表现'],'练习机会和学习结果是同一件事吗？')},
 {'id':'reading-causal','course_id':'reading','title':'相关之后，还要追问','objective':'能提出替代解释，限制因果结论。','minutes':15,
  'sections':[
   {'title':'一起变化不自动说明原因','text':'如果两个变化同期发生，可能存在共同原因或其他变化。需要比较条件、时间顺序和替代解释，才能更谨慎地讨论因果。'},
   {'title':'用具体材料说明局限','text':'某班调整学习安排后作业完成率上升，但同期也降低了作业难度。这是本课程自编的合成情境；它不能单独证明安排调整造成了提升。'},
   {'title':'提出下一份需要的证据','text':'可以比较难度相近的作业、查看调整前后的趋势，或设置合适对照。提出证据应服务当前结论，不能只背诵“相关不等于因果”。'}],
  'practice':written('reading-causal-p','某学习小组使用新工具后正确率上升，同时练习题也变简单了。能否仅据此认定新工具有效？请说明理由。',['明确当前信息不足以单独归因','提到题目难度变化这一替代解释','提出至少一项有针对性的比较'],'除了工具，还有哪个条件也改变了？'),
  'review':written('reading-causal-r','一家公司更换办公地点后效率提升，同时也招聘了更多员工。请给出一个谨慎结论与后续核查办法。',['结论不超出已知事实','识别员工数量这一其他变化','提出针对性的核查或比较'],'把已观察到的变化和原因判断分开写。')},
 {'id':'reading-argument','course_id':'reading','title':'把观点连到证据','objective':'能用主张、依据和限制组织短论证。','minutes':15,
  'sections':[
   {'title':'论证有可以追踪的连接','text':'一个简短论证可以包含主张、依据以及依据如何支持主张。观点不必与别人相同，但连接需要成立。'},
   {'title':'主动说明限制','text':'样本少、来源不确定或场景不同，都可能限制结论。说明限制能够帮助读者判断适用范围，不是简单给每句话加“可能”。'},
   {'title':'为读者留下核查入口','text':'把数据、原文或作品的位置写清楚。对自己的解释也保留修正入口，发现新证据后可以更新结论。'}],
  'practice':written('reading-argument-p','请用80—150字论证一个你想改善的学习习惯，写出主张、可以观察的依据，以及结论的适用限制。',['提出明确而具体的主张','给出可以观察或核查的依据','解释依据与主张的连接','说明至少一个限制'],'先写“我想改变什么”，再写“用什么实际表现检查”。'),
  'review':written('reading-argument-r','请评价：“我连续三天晚饭后阅读，所以晚饭后一定是所有人最有效的阅读时间。”并给出更合适的表述。',['指出个人短期观察的范围','避免把个人观察推广到所有人','给出更有限且可检查的结论'],'样本是谁，观察了多久，结论又说到了谁？')},
]

from .curriculum_20261109 import additional_lessons,update_courses
LESSONS.extend(additional_lessons())
update_courses(COURSES)
COURSE_MAP = {c['id']: c for c in COURSES}
DECLARED_PREREQUISITES = {
    'python-condition': ['python-variable'],
    'python-loop': ['python-variable', 'python-condition'],
}
LESSON_MAP = {l['id']: l for l in LESSONS}
for _lesson in LESSONS:
    if _lesson.get('prerequisites'):DECLARED_PREREQUISITES[_lesson['id']]=list(_lesson['prerequisites'])
TASK_MAP = {l[k]['id']: (l, l[k], k) for l in LESSONS for k in ('practice', 'review')}

from .packs import install
install(LESSONS, TASK_MAP)


def public_course(course):
    result=deepcopy(course)
    result['lesson_count']=len([l for l in LESSONS if l['course_id']==course['id']])
    result['minutes']=sum(l['minutes'] for l in LESSONS if l['course_id']==course['id'])
    result['source_label']='知行伴学自编学习材料 · 课程依据见参考链接'
    return result


def public_task(task):
    allowed={'id','version','kind','prompt','options','criteria','purpose','objective_ids','source_refs','family_id','exposure_group_id','lesson_id','context_table','origin','synthetic_scenario','transfer_claim','independent_transfer_review'}
    return {key:deepcopy(value) for key,value in task.items() if key in allowed}


def public_lesson(lesson):
    result=deepcopy(lesson)
    result['practice']=public_task(lesson['practice'])
    result['review']=public_task(lesson['review'])
    result['tasks']=[public_task(task) for task in lesson.get('tasks',[])]
    result['source_label']='知行伴学自编讲义 · '+lesson['title']
    return result
