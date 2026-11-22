"""seed part4：资料 + 笔记 + 回读校验。不提交任何作答（避免重复暴露）。"""
import json
import sys
import urllib.request
import uuid

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'http://127.0.0.1:8766'
S_MATH = 'space_233c3ad66c0f41a2963cc2d876577d81'
S_PROG = 'space_ae10f324471548db9f6655cfd531588c'
S_READ = 'space_501c4f921a1140ddb914592ed7fee44a'


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def rid(tag):
    return f'promo-{tag}-{uuid.uuid4().hex[:12]}'


def main():
    m1 = call('POST', '/api/materials', {
        'title': '阅览室各时段座位占用记录（演示）',
        'text': '周一 09:00 可用 42 占用 18；周一 14:00 可用 42 占用 31；周三 09:00 可用 38 占用 12；'
                '周三 14:00 可用 38 占用 29；周五 09:00 可用 45 占用 20；周五 14:00 可用 45 占用 36。'
                '占用率高是否等于体验好，还需要别的证据。',
        'evidence_kind': 'authored',
        'request_id': rid('mat'),
    })
    m2 = call('POST', '/api/materials', {
        'title': '我自己整理的百分比基准量笔记',
        'text': '连续变化时，第二次的基准是第一次变化后的量，不是最初的量。'
                '先写下每一步的基准，再算，就不容易错。',
        'evidence_kind': 'self_reported',
        'request_id': rid('mat'),
    })
    print('materials:', m1, m2)
    for sid, title, text in (
        (S_MATH, '基准量：先问"相对谁"',
         '看到"增长了 20%"先停一下：20% 是相对哪个量？把基准写出来，数字才有意义。'
         '今天两道题都是栽在把新量当基准。'),
        (S_READ, '事实与判断的三条自查',
         '1 能不能指出核查它的方法？2 句子里有没有评价性形容词？3 我的结论比证据多走了几步？'),
        (S_PROG, '循环里先写"每轮变什么"',
         '推代码前先列：循环变量、累加器、筛选条件。三者分开写，预测结果就不容易乱。'),
    ):
        r = call('POST', '/api/notes', {'session_id': sid, 'title': title, 'text': text,
                                        'request_id': rid('note')})
        print('note:', r)

    for sid, name in ((S_MATH, 'math'), (S_PROG, 'prog'), (S_READ, 'read')):
        ev = call('GET', f'/api/sessions/{sid}/evidence')
        print(f'=== {name} evidence ===')
        print(json.dumps(ev, ensure_ascii=False, indent=1)[:1600])
    print('--- next(math) ---')
    print(json.dumps(call('GET', f'/api/sessions/{S_MATH}/next'), ensure_ascii=False)[:500])
    print('--- knowledge ---')
    k = call('GET', '/api/knowledge')
    print(json.dumps(k, ensure_ascii=False)[:700])
    print('SEED PART4 OK')


if __name__ == '__main__':
    main()
