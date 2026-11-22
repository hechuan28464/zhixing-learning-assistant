"""Check candidate contest content contracts; does not publish or touch learner data."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '数据补充_20261106'
PACK = DEST / '候选课程包'


def rows(relative):
    return [json.loads(line) for line in (PACK / relative).read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    checks = []
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))

    tasks = rows('public/tasks.jsonl'); objectives = rows('public/objectives.jsonl')
    sources = rows('public/sources.jsonl'); contracts = rows('private/assessment_contracts.jsonl')
    cards = rows('private/misconceptions.jsonl'); relations = rows('public/relations.jsonl')
    task_map = {t['id']: t for t in tasks}; source_ids = {s['id'] for s in sources}
    objective_ids = {o['id'] for o in objectives}; private = {c['task_id']: c for c in contracts}
    check('unique_task_ids', len(task_map) == len(tasks))
    check('unique_objective_ids', len(objective_ids) == len(objectives))
    check('unique_source_ids', len(source_ids) == len(sources))
    check('one_private_contract_per_task', len(private) == len(contracts) == len(tasks) and set(private) == set(task_map))
    for task in tasks:
        check(task['id'] + ':source_and_objective_links', bool(task['source_refs']) and
              set(task['source_refs']) <= source_ids and bool(task['objective_ids']) and set(task['objective_ids']) <= objective_ids)
        check(task['id'] + ':version_binding', private[task['id']]['version'] == task['version'])
        check(task['id'] + ':no_private_fields', not ({'answer', 'hint', 'explanation', 'misconception_by_option', 'hidden_tests'} & set(task)))
        check(task['id'] + ':exposure_group', bool(task.get('exposure_group_id')))
        if task['kind'] == 'choice':
            ids = [o['id'] for o in task['options']]
            check(task['id'] + ':choice_contract', len(ids) == len(set(ids)) >= 2 and private[task['id']].get('answer') in ids)
        else:
            check(task['id'] + ':written_has_criteria', bool(task.get('criteria')) and 'answer' not in private[task['id']])
            check(task['id'] + ':written_not_auto_passed', private[task['id']].get('evaluation') == 'pending_rubric_review')
    check('objective_sources_exist', all(set(o['source_refs']) <= source_ids for o in objectives))
    check('relation_endpoints_exist', all(r['source'] in objective_ids and r['target'] in objective_ids for r in relations))
    check('candidate_bridge_no_mastery_sharing', all(r.get('may_auto_share_mastery') is False for r in relations if r['type'] == 'bridge_candidate'))
    check('misconception_links_and_wrong_options', all(
        c['trigger_task_id'] in task_map and c['remediation_task_id'] in task_map
        and c['trigger_option'] in {o['id'] for o in task_map[c['trigger_task_id']]['options']}
        and c['trigger_option'] != private[c['trigger_task_id']]['answer']
        and c.get('requires_confirmation') is True for c in cards))
    with (PACK / 'public/reading_room_observations.csv').open(encoding='utf-8-sig', newline='') as stream:
        observations = list(csv.DictReader(stream))
    check('synthetic_rows_and_bounds', len(observations) == 12 and all(
        0 <= int(r['occupied_seats']) <= int(r['available_seats']) and r['data_origin'] == 'authored_demo_not_real_measurement' for r in observations))
    check('expected_inventory', len(tasks) == 39 and len(objectives) == 12 and len(cards) == 18 and len(sources) == 22)
    manifest = json.loads((DEST / '校验/课程数据校验.json').read_text(encoding='utf-8'))
    check('manifest_hashes', all(hashlib.sha256((PACK / item['path']).read_bytes()).hexdigest() == item['sha256'] for item in manifest['files']))
    result = dict(purpose='competition_candidate_data_checks', production_writes=False, runtime_loaded=False,
                  passed=all(c['passed'] for c in checks), checks_total=len(checks),
                  failed=[c for c in checks if not c['passed']], checks=checks,
                  task_kinds=dict(Counter(t['kind'] for t in tasks)),
                  task_purposes=dict(Counter(t['purpose'] for t in tasks)),
                  human_subjects=0, expert_review_claimed=False,
                  limits='Schema, references and selected arithmetic checks; not a teaching-effect experiment or complete expert content review.')
    output = DEST / '校验/候选包结构与隔离检查.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('passed', 'checks_total', 'failed', 'task_kinds', 'task_purposes')}, ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
