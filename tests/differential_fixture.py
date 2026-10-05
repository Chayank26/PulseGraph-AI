"""Synthetic provider for workflow regression tests; never a production fallback."""
import json


class SyntheticProvider:
    def generate(self, payload, schema):
        candidates = []
        for key, finding in payload['findings'].items():
            if finding['status'] != 'present':
                continue
            pair = {'chest_pain': ('Acute Coronary Syndrome / NSTEMI','aha-chest-pain-2021-summary'),
                    'breathlessness': ('Pulmonary Embolism','nice-ng158-1.1.17')}.get(finding['symptom'])
            if pair:
                candidates.append(dict(condition_name=pair[0], supporting_ids=[key],contradicting_ids=[],
                                       missing_ids=[],evidence_ids=[pair[1]]))
        return json.dumps(dict(outcome='candidates' if candidates else 'abstain',
            reason='candidate_review' if candidates else 'outside_scope', candidates=candidates))


def install(monkeypatch):
    monkeypatch.setattr('src.agents.diagnostic.configured_provider', lambda: SyntheticProvider())
