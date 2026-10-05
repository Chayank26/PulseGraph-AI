"""Synthetic workflow regression gate and evaluator integrity checks."""
import json
import socket
import pytest
from pydantic import ValidationError
from src.evaluation import triage

CASES = triage.load_cases()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Synthetic evaluation must not contact external services')
    monkeypatch.setattr(socket.socket, 'connect', blocked)


@pytest.mark.parametrize('case', CASES, ids=[case.id for case in CASES])
def test_synthetic_workflow(case):
    result = triage.assess_case(case)
    # An exception is an evaluator/runtime error, never an expected clinical gap.
    if result['outcome'] == 'ERROR':
        pytest.fail(result['error'], pytrace=True)
    assert result['observed'] is not None
    if case.known_gap:
        assert result['outcome'] == 'KNOWN_GAP', result
        pytest.xfail(case.known_gap)
    assert not result['mismatches'], result


def test_errors_are_not_classified_as_known_gaps(monkeypatch):
    case = next(case for case in CASES if case.known_gap)
    def fail(_):
        raise RuntimeError('Injected runtime failure')
    monkeypatch.setattr(triage, 'replay', fail)
    assert triage.assess_case(case)['outcome'] == 'ERROR'


def test_fixed_known_gap_requires_reclassification(monkeypatch):
    case = next(case for case in CASES if case.known_gap)
    monkeypatch.setattr(triage, 'replay', lambda _: case.expected.model_dump(exclude_unset=True))
    assert triage.assess_case(case)['outcome'] == 'UNEXPECTED_PASS'


def test_invalid_expectation_and_duplicate_id_rejected(tmp_path):
    payload = CASES[0].model_dump(mode='json', exclude_unset=True)
    payload['expected'] = {'misspelled_result': 'END'}
    with pytest.raises(ValidationError):
        triage.EvaluationCase.model_validate(payload)
    path = tmp_path/'cases.json'
    payload = CASES[0].model_dump(mode='json', exclude_unset=True)
    path.write_text(json.dumps([payload,payload]))
    with pytest.raises(ValueError, match='unique'):
        triage.load_cases(path)


def test_report_counts_and_expansion_gate(monkeypatch):
    outcomes = iter(['PASS','KNOWN_GAP','FAIL','ERROR','UNEXPECTED_PASS'])
    monkeypatch.setattr(triage,'assess_case',lambda case: {'id':case.id,'category':case.category,'outcome':next(outcomes)})
    report = triage.evaluate(CASES[:5])
    assert report['total'] == 5
    assert sum(report['counts'].values()) == 5
    assert not report['regression_gate_passed']
    assert not report['expansion_ready']
    assert report['corpus_sha256']
    assert report['source_sha256']['src/core/routing.py']
    assert 'not clinical accuracy' in report['scope']
