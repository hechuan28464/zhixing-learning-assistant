"""seed 续跑：reading-fact-r 开放题 + 资料/笔记 + 回读校验。

seed_demo_data.py 在 reading-fact-r 处中断（开放题 answer 为 None），
数学/编程部分已落库。本脚本只补剩余步骤，不重建 session。
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


def main():
    # session id 从 .qa/promo-capture-20261108/records.sqlite3 直查得到
    s_math = 'space_233c3ad66c0f41a2963cc2d876577d81'
    s_prog = 'space_ae10f324471548db9f6655cfd531588c'
    s_read = 'space_501c4f921a1140ddb914592ed7fee44a'

    # 开放题：提交文字作答 => 恒为待复核（产品的诚实设计）
    opened = call('POST', f'/api/sessions/{s_read}/tasks/open', {'task_id': 'reading-fact-r'})
    run_id = opened['run_id']
    res = call('POST', f'/api/sessions/{s_read}/attempts', {
        'run_id': run_id,
        'response': '第二句可以被核对：它给出了具体的时间与数量。第一句是评价，因为它用了"最好"这样的判断词。',
        'request_id': rid('att'),
    })
    print('written attempt ->', json.dumps(res, ensure_ascii=False)[:300])

    # 资料
    call('POST', '/api/materials', {
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
    # 笔记
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

    # 回读校验
    for sid, name in ((s_math, 'math'), (s_prog, 'prog'), (s_read, 'read')):
        ev = call('GET', f'/api/sessions/{sid}/evidence')
        dims = ev.get('dimensions') or ev
        print(f'--- {name} ---')
        print(json.dumps(ev, ensure_ascii=False)[:700])
    print('--- next(math) ---')
    print(json.dumps(call('GET', f'/api/sessions/{s_math}/next'), ensure_ascii=False)[:400])
    print('--- knowledge counts ---')
    k = call('GET', '/api/knowledge')
    print(json.dumps(k, ensure_ascii=False)[:500])
    print('SEED PART2 OK')


if __name__ == '__main__':
    main()
