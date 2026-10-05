"""Offline developer-authored retrieval regression benchmark, not clinical evaluation."""
import hashlib
import json
from datetime import date
from pathlib import Path
from src.core.evidence import retrieve, CORPUS_PATH
from src.core.state import DiagnosticDifferential

CASES = Path(__file__).resolve().parents[1] / 'tests/fixtures/evaluation/evidence_cases.json'


def evaluate():
    raw = CASES.read_bytes()
    rows = []
    for case in json.loads(raw):
        evidence, review = retrieve([DiagnosticDifferential(condition_name=case['claim'],
            likelihood='Not estimated', rationale='Synthetic retrieval regression')], today=date.fromisoformat(case['date']))
        actual = [item.document_id for item in evidence]
        passed = (actual == case['documents'] and
                  all(item.support_status == 'RELATED_CONTEXT_ONLY' and item.relevance_score is None for item in evidence) and
                  review['claims'][0]['status'] == ('RELATED_CONTEXT_ONLY' if actual else 'INSUFFICIENT_SUPPORT'))
        rows.append({'id': case['id'], 'passed': passed, 'expected_documents': case['documents'],
                     'actual_documents': actual, 'limitation': case.get('limitation')})
    return {'corpus_sha256': hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(),
            'cases_sha256': hashlib.sha256(raw).hexdigest(), 'total': len(rows),
            'passed': sum(row['passed'] for row in rows), 'clinical_validation': False,
            'limitations': ['Developer-authored expectations test declared behavior, not clinical retrieval quality.',
                           'Synonym and negation cases document limitations; they are not successful clinical assessments.'],
            'cases': rows}


if __name__ == '__main__':
    report = evaluate()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['total'] == report['passed'] else 1)
