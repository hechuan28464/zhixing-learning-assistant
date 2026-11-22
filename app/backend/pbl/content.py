from .engine import PROJECT
STAGES=['讲解','决策','计划','代码','测试','测验','复盘']
ROLES=['discussion','discussion','planner','coder','assessment','assessment','mentor']
ROLE_LABELS={'discussion':'概念与决策引导','planner':'规划引导','coder':'实现与检查','mentor':'反思引导','assessment':'独立检查'}
STARTER='''def summarize(records):
    """按主题累计分钟数，返回一个新字典；不修改 records。"""
    # 在这里写下你的实现
    raise NotImplementedError("请先按自己的计划实现")
'''
LESSON='''这个项目把变量、条件与循环连在一起：读取多条学习记录，按主题合并分钟数。
每条记录含 topic 和 minutes。先说明输入与输出，再想想同一个主题出现两次时，应该保留什么。
你可以用字典保存“主题→累计分钟数”，通过循环逐条更新。先写计划，再用实际结果检查；代码通过与独立理解是不同证据。'''
PLAN_HELP='写清输入与输出、累计规则、空列表处理，以及准备怎样检查结果。'
# Expected results remain on the web host; the execution worker receives inputs only.
CASES=[{'id':'merge','label':'同主题汇总','input':[{'topic':'数学','minutes':15},{'topic':'阅读','minutes':20},{'topic':'数学','minutes':10}],'expected':{'数学':25,'阅读':20}},
       {'id':'empty','label':'空记录','input':[],'expected':{}},
       {'id':'zero','label':'零分钟与新主题','input':[{'topic':'编程','minutes':0},{'topic':'编程','minutes':8}],'expected':{'编程':8}}]

def public_project():
    return {'id':PROJECT['id'],'title':PROJECT['title'],'version':'1.0.0','description':PROJECT['intro']['say'],
            'contract':PROJECT['milestones'][0]['contract'],'stages':STAGES,'lesson':LESSON,'starter':STARTER,
            'decisions':[{k:d[k] for k in ['id','decisionPrompt','requiresRationale']} for d in PROJECT['decisions']],
            'quiz':[{'q':q['q'],'options':q['options']} for q in PROJECT['milestones'][0]['quiz']],
            'source':{'name':'OpenMAIC PBL v3 domain','version':'1.4.0','commit':'795420c12f7846577468fc7831437db6eb957e14','host':'知行伴学适配实现'}}
