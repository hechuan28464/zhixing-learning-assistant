"""Assemble contest planning attachments from an explicit local allowlist."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ATTACH = ROOT / '实施方案附件'


def write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    data = [
        ('C00', '11-06', 'completed_planning_and_data_only', [], '现状审计、候选数据、结构检查、竞赛方案', '文件与结果已生成；不代表应用功能已接入'),
        ('C01', '11-06', 'planned', ['C00'], '一致性备份、最小迁移、课程包注册和公开转换', '旧18题兼容，新任务可打开，私密契约不进入前端'),
        ('C02', '11-07', 'planned', ['C01'], '服务端诊断、错因候选和补救选择，联调首页与学习页', '不同作答产生不同且有依据的下一步'),
        ('C03', '11-07', 'planned', ['C01', 'C02'], '状态字段和阅读分项候选反馈', '受助、待复核明确，引用原作答可定位'),
        ('C04', '11-08', 'planned', ['C02', 'C03'], '跨科共同问题、知识空间和搜索联调', '目标分别归属，来源和记录可打开可恢复'),
        ('C05', '11-06..11-08', 'pending_target_server_access', ['C00'], '现有Linux部署和PBL真实执行验收', '空实现失败、正确实现通过、超时清理、版本失效和重启恢复'),
        ('C06', '11-08..11-09', 'planned', ['C02', 'C03', 'C04'], '核心旅程、重试、迟到响应和备份恢复验收', '无数据丢失、假完成和重复副作用；C05执行分支另需服务器'),
        ('C07', '11-09', 'planned', ['C06'], '版本冻结、干净目录复现、提交包和演示材料', '清单与实际版本相符，未验收运行能力关闭并说明'),
        ('C08', '11-10', 'planned', ['C07'], '最终提交物核对及阻断问题修复', '以真实提交时刻为准；提交入口操作需具备权限者完成'),
    ]
    tasks = [dict(id=i, date='2026-' + d, status=s, dependencies=deps, deliverable=out,
                  acceptance=accept, executor='Codex', priority='P0' if i != 'C00' else 'completed')
             for i, d, s, deps, out, accept in data]
    write(ATTACH / '竞赛工作清单_20261106.json', dict(
        purpose='competition_delivery_not_paper_experiment', deadline='2026-11-10',
        deadline_time_known=False, team_members=3, coding_executor='Codex', tasks=tasks,
        not_required_before_submission=['KT training', 'large student dataset', 'expert panel',
                                        'three-group controlled study', 'statistical significance',
                                        '30-day simulation', 'full OpenMAIC deployment']))
    docs = [ROOT / '竞赛后端落地与数据接入实施方案_20261106.md',
            ROOT / '数据补充_20261106/README.md',
            ROOT / '数据补充_20261106/竞赛演示操作单.md',
            ROOT / '数据补充_20261106/来源快照/使用说明.md',
            ROOT / '调研补充_20261106/竞赛可用结论与来源核对.md']
    missing = []
    local_links = 0
    for doc in docs:
        for target in re.findall(r'\]\(([^)]+)\)', doc.read_text(encoding='utf-8')):
            if target.startswith(('https://', 'http://', '#')):
                continue
            local_links += 1
            destination = doc.parent / unquote(target.split('#')[0])
            if not destination.exists():
                missing.append(dict(document=str(doc.relative_to(ROOT)), target=target))
    validation = json.loads((ROOT / '数据补充_20261106/校验/候选包结构与隔离检查.json').read_text(encoding='utf-8'))
    downloads = json.loads((ROOT / '数据补充_20261106/来源快照/下载清单.json').read_text(encoding='utf-8'))
    snapshots_valid = all(r['downloaded'] and hashlib.sha256(
        (ROOT / '数据补充_20261106/来源快照' / r['local_file']).read_bytes()).hexdigest() == r['sha256']
        for r in downloads['sources'])
    archive_path = ATTACH / '竞赛课程候选数据包_20261106.zip'
    # Only this newly authored data directory: no .env, database, exports or user history.
    included = sorted(p for p in (ROOT / '数据补充_20261106').rglob('*') if p.is_file())
    with ZipFile(archive_path, 'w', ZIP_DEFLATED) as archive:
        for path in included:
            archive.write(path, path.relative_to(ROOT).as_posix())
    checks = dict(document_files=len(docs), local_links_checked=local_links, missing_links=missing,
                  candidate_assertions_passed=validation['passed'],
                  candidate_assertions_total=validation['checks_total'],
                  official_snapshots_hashes_passed=snapshots_valid,
                  archive_files=len(included), archive_path=archive_path.relative_to(ROOT).as_posix(),
                  archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                  application_backend_changed=False, production_database_written=False,
                  candidate_runtime_loaded=False, live_linux_execution_verified=False,
                  all_application_tests_rerun=False)
    checks['passed'] = not missing and validation['passed'] and snapshots_valid
    write(ATTACH / '竞赛方案与数据交付校验_20261106.json', checks)
    print(json.dumps(checks, ensure_ascii=False))
    if not checks['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
