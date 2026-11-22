"""Read-only contest inventory. Never import the application or read private settings."""
import ast
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'
OUT = ROOT / '实施方案附件/后端现状审计_20261106.json'


def main():
    routes = []
    for relative, prefix in [('backend/main.py', ''), ('backend/pbl/routes.py', '/api/pbl')]:
        tree = ast.parse((APP / relative).read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                    and deco.func.attr in ('get', 'post', 'patch', 'delete', 'put')
                    and deco.args and isinstance(deco.args[0], ast.Constant)):
                    routes.append(dict(method=deco.func.attr.upper(), path=prefix + deco.args[0].value,
                                       file=relative, line=node.lineno))
    tests = {}
    for path in sorted((APP / 'tests').glob('test_*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        tests[path.name] = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                               and n.name.startswith('test_') for n in ast.walk(tree))
    db_path = APP / 'data/private/learning.sqlite3'
    database = dict(path='app/data/private/learning.sqlite3', access='mode=ro',
                    queried_content='schema names and aggregate counts only', exists=db_path.exists())
    if db_path.exists():
        with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True) as con:
            tables = [row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            database['tables'] = {name: con.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0] for name in tables}
            database['table_count'] = len(tables)
    runtime = {}
    for name, endpoint in [('health', '/api/health'), ('pbl_catalog', '/api/pbl/catalog')]:
        try:
            with urlopen('http://127.0.0.1:8765' + endpoint, timeout=4) as response:
                payload = json.load(response)
                item = dict(http_status=response.status)
                if name == 'health':
                    item.update({k: payload.get(k) for k in ('ok', 'application', 'version', 'mode')})
                    model = payload.get('model', {})
                    item['model_configured'] = model.get('configured') if isinstance(model, dict) else None
                else:
                    # Do not persist arbitrary responses, configuration, or model settings.
                    item['top_level_keys'] = list(payload) if isinstance(payload, dict) else ['list']
                runtime[name] = item
        except Exception as exc:
            runtime[name] = dict(available=False, error_type=type(exc).__name__)
    records = []
    paths = [ROOT / '教育Agent参考项目拆解.md', ROOT / 'LearnLM与EduClaw-Bench数据扒取.md',
             ROOT / '跨学科个性化学习Agent竞赛实施方案_20261102.md',
             APP / 'backend/main.py', APP / 'backend/service.py', APP / 'backend/content.py',
             APP / 'backend/store.py', APP / 'backend/pbl/routes.py',
             ROOT / '参考项目/_provenance/source-manifest.json']
    paths += sorted((APP / 'test-reports').glob('**/REPORT.md'))
    for path in paths:
        if path.exists():
            records.append(dict(path=path.relative_to(ROOT).as_posix(),
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result = dict(observed_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
                  timezone='Asia/Shanghai (UTC+08:00 in 2026)',
                  purpose='competition_delivery_inventory_not_learning_effect_experiment',
                  application_imported=False, production_writes=False, model_calls=0,
                  route_count=len(routes), routes=routes, database=database,
                  test_source_functions=tests, test_source_function_total=sum(tests.values()),
                  tests_rerun_in_this_audit=False, runtime=runtime,
                  docker_cli_on_current_windows_host=shutil.which('docker') is not None,
                  target_linux_server_verified=False, source_hashes=records,
                  warning='Source counts and historical test reports do not prove live Linux execution or complete personalization.')
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(OUT), routes=len(routes), tables=database.get('table_count'),
                          test_functions=sum(tests.values()), runtime=runtime), ensure_ascii=False))


if __name__ == '__main__':
    main()
