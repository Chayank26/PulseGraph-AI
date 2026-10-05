"""Replay synthetic cases through the real graph with isolated memory checkpoints."""
from collections import Counter
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from langgraph.checkpoint.memory import MemorySaver

from src.core.data_requests import apply_response_to_state, resolve_request
from src.core.graph import build_clinical_graph
from src.core.imaging import ImagingDecision
from src.core.routing import PathwayDecisions
from src.core.state import ClinicianIdentity, PatientDemographics, VitalSigns
from src.core.urgency import UrgencyContext
from config.settings import settings

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = ROOT / 'tests/fixtures/evaluation/triage_cases.json'


class Inputs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    complaint: str
    age: int | None = 50
    notes: list[str] = Field(default_factory=list)
    vitals: VitalSigns | None = None
    urgency_context: UrgencyContext | None = None
    pathway_decisions: PathwayDecisions | None = None
    imaging_decision: ImagingDecision | None = None
    image_path: str | None = None


class Expected(BaseModel):
    model_config = ConfigDict(extra='forbid')
    next_node: str | None = None
    step: str | None = None
    symptoms: dict[str, str] | None = None
    groups: list[str] | None = None
    pathways: dict[str, str] | None = None
    scores: dict[str, float] | None = None
    questions: list[dict[str, Any]] | None = None
    urgency_status: str | None = None
    imaging_status: str | None = None


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    inputs: Inputs
    responses: list[dict[str, Any]] = Field(default_factory=list)
    expected: Expected
    known_gap: str | None = None

    @model_validator(mode='after')
    def meaningful_expectations(self):
        if not self.expected.model_fields_set:
            raise ValueError('Each case must have at least one explicit expectation')
        if self.known_gap is not None and not self.known_gap.strip():
            raise ValueError('Known gaps need an explanation')
        return self


def load_cases(path: Path = DEFAULT_CASES) -> list[EvaluationCase]:
    raw = json.loads(path.read_text())
    cases = [EvaluationCase.model_validate(value) for value in raw]
    if not cases or len({case.id for case in cases}) != len(cases):
        raise ValueError('Evaluation requires a nonempty corpus with unique case IDs')
    return cases


def replay(case: EvaluationCase) -> dict:
    inputs = case.inputs
    graph = build_clinical_graph(checkpointer=MemorySaver())
    config = {'configurable': {'thread_id': case.id}, 'recursion_limit': 60}
    state = {'patient_id': 'SYNTHETIC', 'demographics': PatientDemographics(
        patient_id='SYNTHETIC', age=inputs.age, chief_complaint=inputs.complaint),
        'raw_notes': inputs.notes, 'vitals': inputs.vitals,
        'urgency_context': inputs.urgency_context.model_dump() if inputs.urgency_context else None,
        'pathway_decisions': inputs.pathway_decisions.model_dump() if inputs.pathway_decisions else None,
        'imaging_decision': inputs.imaging_decision.model_dump() if inputs.imaging_decision else None,
        'image_path': inputs.image_path,
        'authenticated_clinician': ClinicianIdentity(doctor_id='SYNTHETIC', full_name='Synthetic evaluator', department='Test'),
        'current_step': 'initialized', 'urgency_resume_node': 'triage'}
    graph.invoke(state, config)
    questions = []
    responses = iter(case.responses)
    for _ in range(16):
        snapshot = graph.get_state(config)
        pending = snapshot.values.get('pending_data_requests', [])
        if snapshot.next != ('data_request_review',) or not pending:
            if next(responses, None) is not None:
                raise ValueError('Scripted response remains after the workflow stopped')
            break
        request = pending[0]
        fields = sorted('$urgency_ack' if f.field_key.startswith('urgency_review_') else f.field_key
                        for f in request.required_fields)
        questions.append({'agent': request.requesting_agent, 'pathway': request.pathway_name, 'fields': fields})
        answer = next(responses, None)
        if answer is None:
            break
        answer = dict(answer)
        if '$urgency_ack' in answer:
            if request.requesting_agent != 'urgency_check':
                raise ValueError('Urgency acknowledgement supplied at the wrong checkpoint')
            answer[request.required_fields[0].field_key] = answer.pop('$urgency_ack')
        allowed = {f.field_key for f in request.required_fields + request.optional_fields}
        if set(answer) - allowed:
            raise ValueError('Response fields do not match the active request')
        resolved = resolve_request(request, answer)
        update = apply_response_to_state(snapshot.values, answer)
        update.update(pending_data_requests=[resolved], resolved_data_requests=[resolved],
                      active_data_request_id=resolved.request_id)
        graph.update_state(config, update, as_node='data_request_review')
        graph.invoke(None, config)
    else:
        raise ValueError('Evaluation exceeded its 16-checkpoint bound')
    snapshot = graph.get_state(config)
    value = snapshot.values
    presentation = value.get('presentation') or {}
    routing = presentation.get('routing') or {}
    return {'next_node': snapshot.next[0] if snapshot.next else 'END',
        'step': value.get('current_step'),
        'symptoms': {s['symptom']: s['status'] for s in presentation.get('symptoms', [])},
        'groups': sorted(routing.get('groups', {})),
        'pathways': {p['key']: p['status'] for p in routing.get('pathways', [])},
        'scores': {s.score_name: s.value for s in value.get('risk_scores', [])},
        'questions': questions, 'urgency_status': (value.get('urgency') or {}).get('status'),
        'imaging_status': (presentation.get('imaging_plan') or {}).get('status')}


def assess_case(case: EvaluationCase) -> dict:
    expected = case.expected.model_dump(exclude_unset=True)
    try:
        actual = replay(case)
        mismatches = {key: {'expected': wanted, 'observed': actual[key]}
                      for key, wanted in expected.items() if wanted != actual[key]}
        outcome = ('KNOWN_GAP' if case.known_gap else 'FAIL') if mismatches else ('UNEXPECTED_PASS' if case.known_gap else 'PASS')
        return {'id': case.id, 'category': case.category, 'outcome': outcome, 'known_gap': case.known_gap,
                'expected': expected, 'observed': actual, 'mismatches': mismatches}
    except Exception as exc:
        # Exceptions are never hidden behind a known-gap label.
        return {'id': case.id, 'category': case.category, 'outcome': 'ERROR',
                'error': f'{type(exc).__name__}: {exc}'}


def evaluate(cases: list[EvaluationCase], corpus_path: Path = DEFAULT_CASES) -> dict:
    results = [assess_case(case) for case in cases]
    counts = dict(Counter(result['outcome'] for result in results))
    source_files = sorted((ROOT / 'src').rglob('*.py')) + [ROOT / 'config/settings.py']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}
    return {'evaluation_version': 'synthetic-triage-v1',
        'scope': 'Developer-authored synthetic graph replay; not clinical accuracy, independent validation, API authorization, or persistence testing.',
        'environment': {'python': platform.python_version(),
            **{name: version(name) for name in ('langgraph', 'pydantic', 'pytest')}},
        'corpus_sha256': hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        'source_sha256': hashes, 'urgency_rules': settings.urgency_rules.model_dump(),
        'total': len(results), 'counts': counts,
        'regression_gate_passed': not any(counts.get(key) for key in ('FAIL', 'ERROR', 'UNEXPECTED_PASS')),
        'expansion_ready': False,
        'expansion_blockers': ['Independent clinician review and an annotated evaluation corpus are absent.',
            'Any known gaps listed below must be assessed before broadening coverage.',
            'Downstream diagnostic and evidence nodes remain bounded demonstration logic.'],
        'results': results}


def markdown_report(report: dict) -> str:
    lines = ['# Synthetic triage evaluation', '', report['scope'], '',
        f"Cases: **{report['total']}**. Outcomes: `{json.dumps(report['counts'], sort_keys=True)}`.", '',
        'Passing regression checks does not authorize clinical deployment or new pathways.', '',
        '| Category | Pass | Known gap | Failure/error/unexpected pass |', '| --- | ---: | ---: | ---: |']
    for category in sorted({r['category'] for r in report['results']}):
        items = [r for r in report['results'] if r['category'] == category]
        counts = Counter(r['outcome'] for r in items)
        lines.append(f"| {category} | {counts['PASS']} | {counts['KNOWN_GAP']} | {sum(counts[k] for k in ('FAIL','ERROR','UNEXPECTED_PASS'))} |")
    lines += ['', '## Cases', '', '| Case | Outcome | Gap or mismatch |', '| --- | --- | --- |']
    for result in report['results']:
        detail = result.get('known_gap') or result.get('error') or (json.dumps(result.get('mismatches')) if result.get('mismatches') else '')
        lines.append(f"| {result['id']} | {result['outcome']} | {detail.replace('|', '/')} |")
    lines += ['', '## Expansion gate', '', *['- ' + reason for reason in report['expansion_blockers']], '',
              'Machine-readable expected and observed values, source hashes, and rule configuration are in the companion JSON report.', '']
    return '\n'.join(lines)
