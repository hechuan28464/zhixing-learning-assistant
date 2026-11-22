"""向隔离 QA 实例注入虚构演示数据（零模型调用、零登录）。

目标：让宣传片截图的每个页面都有"虚构但真实感"的内容，而不是空库废片。
所有数据均为本脚本虚构，不含任何真实学习记录。
"""
import json
import urllib.request
import uuid

BASE = 'http://127.0.0.1:8766'


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def rid(tag):
    return f'promo-{tag}-{uuid.uuid4().hex[:12]}'


def load_answers():
    out = {}
    with open(r'F:\实训伴学4\app\backend\resources\contest-pack-v1\private\assessment_contracts.jsonl',
              encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                c = json.loads(line)
                out[c['task_id']] = c
    return out


ANSWERS = load_answers()
OPTIONS = ['A', 'B', 'C', 'D']


def wrong_option(task_id):
    good = ANSWERS[task_id]['answer']
    for o in OPTIONS:
        if o != good:
            return o
    raise SystemExit('no wrong option for ' + task_id)


def open_and_submit(session, task_id, option, hint_first=False):
    opened = call('POST', f'/api/sessions/{session}/tasks/open', {'task_id': task_id})
    run_id = opened['run_id'] if isinstance(opened, dict) and 'run_id' in opened else opened.get('id')
    if hint_first:
        call('POST', f'/api/sessions/{session}/hints', {'run_id': run_id})
    res = call('POST', f'/api/sessions/{session}/attempts',
               {'run_id': run_id, 'response': option, 'request_id': rid('att')})
    return run_id, res


def main():
    log = []

    # ---- 三个学习空间（虚构目标）----
    s_math = call('POST', '/api/sessions', {
        'course_id': 'mathematics',
        'title': '把百分比和概率用到真实判断里',
        'goal': '想弄清楚新闻里的百分比和概率到底在说什么，别再被基准量绕进去。',
        'daily_minutes': 30,
    })['id']
    s_prog = call('POST', '/api/sessions', {
        'course_id': 'programming',
        'title': '读懂 Python 代码在做什么',
        'goal': '能不看运行结果，自己推出一段循环和条件分支执行后的变量值。',
        'daily_minutes': 25,
    })['id']
    s_read = call('POST', '/api/sessions', {
        'course_id': 'reading',
        'title': '区分事实与判断，把观点连到证据',
        'goal': '读材料时能指出哪句是可核查的事实、哪句是评价，并给自己的判断找证据。',
        'daily_minutes': 20,
    })['id']
    log.append(('sessions', [s_math, s_prog, s_read]))

    # ---- 数学：独立掌握 + 受助 + 补救 ----
    call('POST', f'/api/sessions/{s_math}/lessons/math-reference', {})
    open_and_submit(s_math, 'math-reference-p', ANSWERS['math-reference-p']['answer'])
    open_and_submit(s_math, 'math-reference-r', ANSWERS['math-reference-r']['answer'])
    # 先答错，再要提示，再答对 => 受助完成
    open_and_submit(s_math, 'math-probability-p', wrong_option('math-probability-p'))
    open_and_submit(s_math, 'math-probability-p', ANSWERS['math-probability-p']['answer'], hint_first=True)
    # 错因触发补救
    open_and_submit(s_math, 'math-data-p', wrong_option('math-data-p'))
    open_and_submit(s_math, 'math-data-remedy-20261106', ANSWERS['math-data-remedy-20261106']['answer'])
    # 复核题独立答对 => 覆盖目标
    open_and_submit(s_math, 'math-probability-r', ANSWERS['math-probability-r']['answer'])

    # ---- 编程：独立 + 重复暴露 ----
    call('POST', f'/api/sessions/{s_prog}/lessons/python-loop', {})
    open_and_submit(s_prog, 'python-loop-p', ANSWERS['python-loop-p']['answer'])
    open_and_submit(s_prog, 'python-loop-r', ANSWERS['python-loop-r']['answer'])
    open_and_submit(s_prog, 'python-variable-p', ANSWERS['python-variable-p']['answer'])
    # 同 family 再做一次 => 重复暴露，不算独立
    open_and_submit(s_prog, 'python-loop-r', ANSWERS['python-loop-r']['answer'])

    # ---- 阅读：开放题待复核 + 选择独立 ----
    call('POST', f'/api/sessions/{s_read}/lessons/reading-fact', {})
    open_and_submit(s_read, 'reading-fact-p', '这句话给出了可核查的时间与数量，属于可以核对的陈述，不是评价。')
    open_and_submit(s_read, 'reading-fact-r', ANSWERS['reading-fact-r']['answer'])

    # ---- 资料与笔记 ----
    m1 = call('POST', '/api/materials', {
        'title': '阅览室各时段座位占用记录（演示）',
        'text': '周一 09:00 可用 42 占用 18；周一 14:00 可用 42 占用 31；周三 09:00 可用 38 占用 12；'
                '周三 14:00 可用 38 占用 29；周五 09:00 可用 45 占用 20；周五 14:00 可用 45 占用 36。'
                '占用率高是否等于体验好，还需要别的证据。',
        'evidence_kind': 'authored',
        'request_id': rid('mat'),
    })
    call('POST', '/api/materials', {
        'title': '我自己整理的百分比基准量笔记',
        'text': '连续变化时，第二次的基准是第一次变化后的量，不是最初的量。'
                '先写下每一步的基准，再算，就不容易错。',
        'evidence_kind': 'self_reported',
        'request_id': rid('mat'),
    })
    call('POST', '/api/notes', {
        'session_id': s_math,
        'title': '基准量：先问"相对谁"',
        'text': '看到"增长了 20%"先停一下：20% 是相对哪个量？把基准写出来，数字才有意义。'
                '今天两道题都是栽在把新量当基准。',
        'request_id': rid('note'),
    })
    call('POST', '/api/notes', {
        'session_id': s_read,
        'title': '事实与判断的三条自查',
        'text': '1 能不能指出核查它的方法？2 句子里有没有评价性形容词？3 我的结论比证据多走了几步？',
        'request_id': rid('note'),
    })
    call('POST', '/api/notes', {
        'session_id': s_prog,
        'title': '循环里先写"每轮变什么"',
        'text': '推代码前先列：循环变量、累加器、筛选条件。三者分开写，预测结果就不容易乱。',
        'request_id': rid('note'),
    })
    log.append(('materials', m1))

    # ---- 回读校验 ----
    for sid, name in ((s_math, 'math'), (s_prog, 'prog'), (s_read, 'read')):
        ev = call('GET', f'/api/sessions/{sid}/evidence')
        print(f'--- {name} evidence ---')
        print(json.dumps(ev, ensure_ascii=False)[:900])
    print('--- next(math) ---')
    print(json.dumps(call('GET', f'/api/sessions/{s_math}/next'), ensure_ascii=False)[:400])
    print('--- knowledge ---')
    k = call('GET', '/api/knowledge')
    print(json.dumps(k, ensure_ascii=False)[:600])
    print('SEED OK')


if __name__ == '__main__':
    main()
