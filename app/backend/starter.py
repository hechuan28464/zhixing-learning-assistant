"""Idempotent starter goals and authored reading materials, never fake results."""
from . import service
from .store import db,decode,encode

STARTER_VERSION='starter-20261110-v1'
MATERIALS={
 'mathematics':('百分比与证据：从一个问题开始','知行伴学自编导学；课程目录依据 OpenStax Introductory Statistics 2e',
 '''本资料为项目自编导学，不是教材原文。

学习目标：区分原量、变化量和变化后的量，并解释计算依据。

示例：原价200元上涨10%后为220元，再下调10%时，应以第二次变化开始时的220元为基准。可以先说明“百分比相对于谁”，再列出式子。

学习步骤：阅读当前单元讲义，提交一道起点诊断，根据反馈选择补救，再换一道题检查理解。回答与帮助条件分别保留，未检查长期保持时不作掌握结论。

课程依据：https://openstax.org/details/books/introductory-statistics-2e
可向林知提问：请读取当前讲义，用一个生活例子解释为什么连续百分比变化的基准可能不同。'''),
 'programming':('Python研学：函数输入输出与数据汇总','知行伴学自编导学；Python教材目录与 Harvard CS50 Python 官方公开短课',
 '''本资料为项目自编导学，不是教材原文。

学习目标：说明一个函数接收什么、返回什么，并用实际输入输出检查程序。

实践问题：学习记录包含topic与minutes两个字段。记录为“阅读12分钟、Python20分钟、阅读8分钟”时，可以按主题累计得到阅读20分钟、Python20分钟。应额外检查空列表、重复主题和零分钟，且不修改原始输入。

学习步骤：从课程讲义和短诊断开始，再在项目学习中保存计划、代码和实际检查回执。代码通过与独立理解分别记录。

公开教学视频：https://cs50.harvard.edu/python/shorts/functions/
教材：Python程序设计——从基础开发到数据分析（第2版）·微课版，ISBN 9787302590101。目录对齐不代表原机构认证或授课授权。'''),
 'reading':('观察与推断：带着原文进行讨论','知行伴学自编练习；课程目录依据 Saylor PHIL102',
 '''本资料为项目自编练习场景。

材料：假设某阅览室本月新增20个座位。我们看到两句话。
A：本月新增了20个座位。
B：这是最受欢迎的阅览室。

练习：A是可以直接核对的数量陈述；B还需要“受欢迎”的评价标准、比较对象和相应数据。事实陈述也仍需核对来源，不因写成数字就必然真实。

可以追问：哪一句是观察，哪一句包含推断？判断成立还缺什么资料？是否可能有其他解释？

学习步骤：打开原文，选择加入讨论，引用材料中的具体句子，再检查回答的依据。课程目录：https://learn.saylor.org/course/view.php?id=1255''')
}

def ensure_starters():
    with db() as con:
        profile=decode(con.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0],{})
        if profile.get('starter_content_version')==STARTER_VERSION:return {'created':False}
    sessions=[]
    for course_id,(title,source,text) in MATERIALS.items():
        s=service.create_session(course_id=course_id,request_id=STARTER_VERSION+'-'+course_id)
        service.save_material(title,text,source,s['id'],request_id=STARTER_VERSION+'-material-'+course_id)
        sessions.append(s['id'])
    with db() as con:
        profile=decode(con.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0],{})
        profile['starter_content_version']=STARTER_VERSION
        con.execute('UPDATE settings SET payload=? WHERE id=1',(encode(profile),))
    return {'created':True,'sessions':sessions}
