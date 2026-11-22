"""Build a source deployment bundle from an allowlist, never including local secrets or records."""
from pathlib import Path
import hashlib
import json
import zipfile
import argparse

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'
OUT=APP/'exports'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime',action='store_true',help='Package the locally built runtime instead of editable sources.')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    roots=['app/backend','app/deploy']
    roots+=['app/dist','app/integrations/openmaic/LICENSES'] if args.runtime else ['app/src','app/public','app/vendor','app/integrations']
    selected=[]
    for directory in roots:
        for path in (ROOT/directory).rglob('*'):
            if not path.is_file() or any(part in ('__pycache__','.git','node_modules','.pytest_cache') for part in path.parts):continue
            if path.name.startswith('.env') and not path.name.endswith('.example'):continue
            if path.suffix in ('.pyc','.pyo','.pem','.key','.sqlite3','.db','.log'):continue
            selected.append(path)
    extras=['.dockerignore','app/requirements.txt','app/requirements-lock.txt','app/README.md','scripts/check_model_api.py']
    extras+=['app/integrations/openmaic/bridge.mjs'] if args.runtime else ['app/package.json','app/package-lock.json','app/index.html','app/vite.config.js']
    for name in extras:
        path=ROOT/name
        if path.exists():selected.append(path)
    selected=sorted(set(selected));files=[]
    for path in selected:
        relative=path.relative_to(ROOT).as_posix()
        if relative.startswith(('app/design/','app/data/','app/.qa/','app/test-reports/')):raise ValueError('Private working data in release')
        files.append({'path':relative,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    evidence=APP/'test-reports/implementation-v2-20261107'
    def events(name):
        if not (evidence/name).exists():return []
        result=[]
        for line in (evidence/name).read_text(encoding='utf-8').splitlines():
            try:result.append(json.loads(line))
            except ValueError:pass
        return result
    linux=any(row.get('case')=='complete' and row.get('live_linux') for row in events('acceptance-execution.log'))
    persisted=any(row.get('phase')=='after' and row.get('all_table_hashes_unchanged') for row in events('persistence-after.log'))
    verification={'live_linux_execution_verified':bool(linux),'live_linux_persistence_verified':bool(persisted),'live_llm_verified':False,'model_blocker':'TokenRhythm HTTP 402; ordinary pay-as-you-go credentials pending','teaching_fixture_in_execution_check':True}
    scope='prebuilt runtime' if args.runtime else 'editable source'
    manifest={'date':'2026-11-07','version':'0.3.0','scope':scope+' deployment bundle; no credentials or learner records','files':files,**verification}
    archive=OUT/('zhixing-runtime-20261107.zip' if args.runtime else '知行伴学竞赛后端v2部署源码_20261107.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for path in selected:package.write(path,path.relative_to(ROOT).as_posix())
        package.writestr('RELEASE-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    metadata={'archive':archive.name,'bytes':archive.stat().st_size,'files':len(selected),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),**verification}
    (OUT/('runtime-manifest-20261107.json' if args.runtime else 'source-manifest-20261107.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/('runtime-checksums-20261107.json' if args.runtime else '后端v2部署包校验_20261107.json')).write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False))


if __name__=='__main__':main()
