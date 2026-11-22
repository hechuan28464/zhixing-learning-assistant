"""Bounded official documentation snapshots, not learner logs or a general crawler."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '数据补充_20261106/来源快照'
SOURCES = [
    ('python-control-3.12', 'https://docs.python.org/3.12/tutorial/controlflow.html'),
    ('python-data-3.12', 'https://docs.python.org/3.12/tutorial/datastructures.html'),
    ('python-license-3.12', 'https://docs.python.org/3.12/license.html'),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for source_id, url in SOURCES:
        record = dict(id=source_id, url=url,
                      retrieved_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
                      use='Local reference snapshot; not yet indexed or published in the app')
        try:
            request = Request(url, headers={'User-Agent': 'ZhixingContestReferenceCollector/1.0'})
            with urlopen(request, timeout=20) as response:
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise ValueError('Document exceeds bounded snapshot size')
                if 'text/html' not in response.headers.get('Content-Type', ''):
                    raise ValueError('Expected an HTML documentation page')
                record.update(status=response.status, resolved_url=response.url)
            title = re.search(r'<title>(.*?)</title>', body.decode('utf-8'), re.S)
            filename = source_id + '.html'
            (OUT / filename).write_bytes(body)
            record.update(downloaded=True, local_file=filename, bytes=len(body),
                          sha256=hashlib.sha256(body).hexdigest(),
                          page_title=title.group(1).strip() if title else None)
        except Exception as exc:
            record.update(downloaded=False, error_type=type(exc).__name__)
        records.append(record)
    manifest = dict(purpose='Competition official reference collection', sources=records,
                    license_url='https://docs.python.org/3.12/license.html',
                    production_writes=False, learner_records_collected=False, runtime_indexed=False)
    (OUT / '下载清单.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(downloaded=sum(r['downloaded'] for r in records), total=len(records),
                         files=[r.get('local_file') for r in records]), ensure_ascii=False))
    if not all(r['downloaded'] for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
