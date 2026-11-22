import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.content import LESSONS
from backend.pack_registry import OBJECTIVES


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('STUDY_DB_PATH', str(tmp_path/'learning.sqlite3'))
    with TestClient(app) as client:
        yield client


def space(client, course='mathematics'):
    response = client.post('/api/sessions', json={'course_id': course})
    assert response.status_code == 200, response.text
    return response.json()


def open_task(client, sid, task):
    response = client.post(f'/api/sessions/{sid}/tasks/open', json={'task_id': task})
    assert response.status_code == 200, response.text
    return response.json()['run_id']


def submit(client, sid, task, answer, key):
    run_id = open_task(client, sid, task)
    response = client.post(f'/api/sessions/{sid}/attempts',
                           json={'run_id': run_id, 'response': answer, 'request_id': key})
    assert response.status_code == 200, response.text
    return response.json()


def lesson_dimensions(client, sid, lesson='math-reference'):
    data = client.get(f'/api/sessions/{sid}').json()
    return data['states'][lesson]['dimensions']


def objective_count(lesson='math-reference'):
    return len([oid for oid, objective in OBJECTIVES.items() if objective.get('lesson_id') == lesson])


def test_coverage_reports_lesson_objectives_not_attempt_volume(client):
    sid = space(client)['id']
    submit(client, sid, 'math-reference-diag-20261106', 'C', 'cov-attempt-0001')
    submit(client, sid, 'math-reference-remedy-20261106', 'B', 'cov-attempt-0002')
    submit(client, sid, 'math-reference-r', 'A', 'cov-attempt-0003')
    coverage = lesson_dimensions(client, sid)['coverage']
    total = objective_count()
    assert total >= 1
    assert coverage['value'] == 'partial'
    assert coverage['label'] == '目标1/' + str(total) + '有独立证据'
    assert coverage['objectives'] == {'total': total, 'covered': 1}
    assert coverage['attempt_ids'], '覆盖必须能追到具体作答'
    assert '次作答' not in coverage['label'], '标签不能退回作答次数语义'


def test_coverage_stays_uncovered_without_independent_evidence(client):
    sid = space(client)['id']
    submit(client, sid, 'math-reference-diag-20261106', 'C', 'cov-attempt-0011')
    submit(client, sid, 'math-reference-remedy-20261106', 'B', 'cov-attempt-0012')
    coverage = lesson_dimensions(client, sid)['coverage']
    assert coverage['value'] == 'observed'
    assert coverage['objectives']['covered'] == 0
    assert coverage['label'] == '目标0/' + str(objective_count()) + '有独立证据'
    assert coverage['attempt_ids'] == []


def test_coverage_is_none_before_any_attempt(client):
    sid = space(client)['id']
    coverage = lesson_dimensions(client, sid)['coverage']
    assert coverage['value'] == 'none' and coverage['attempt_ids'] == []


def test_next_step_has_one_object_shape_everywhere(client):
    sid = space(client)['id']
    attempt = submit(client, sid, 'math-reference-diag-20261106', 'C', 'shape-attempt-0001')
    action = attempt['next_step']
    assert isinstance(action, dict), '提交作答不能再返回字符串 next_step'
    assert isinstance(attempt['next_step_reason'], str)
    for key in ('kind', 'task_id', 'lesson_id', 'title', 'reason', 'text'):
        assert key in action, key
    assert action['kind'] == 'remedy'
    assert action['task_id'] == attempt['diagnosis']['remedy_task_id']

    current = client.get(f'/api/sessions/{sid}/next').json()
    assert isinstance(current, dict)
    assert current['task_id'] == attempt['next_step']['task_id'], '两次来源必须指向同一项任务'


def test_conflict_retry_keeps_the_same_action_shape(client):
    sid = space(client)['id']
    run_id = open_task(client, sid, 'math-reference-diag-20261106')
    first = client.post(f'/api/sessions/{sid}/attempts',
                        json={'run_id': run_id, 'response': 'C', 'request_id': 'dup-attempt-0001'})
    assert first.status_code == 200, first.text
    second = client.post(f'/api/sessions/{sid}/attempts',
                         json={'run_id': run_id, 'response': 'A', 'request_id': 'dup-attempt-0002'})
    assert second.status_code == 409, second.text
    retry = second.json()['retry']
    assert isinstance(retry, dict)
    for key in ('kind', 'task_id', 'lesson_id', 'reason'):
        assert key in retry, key
    assert retry['task_id'] != run_id
