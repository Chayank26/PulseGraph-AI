from test_triage_foundation import client
from test_optional_imaging import start, decision
from src.core.diagnostic import input_fingerprint
from src.core.graph import feedback_processor_node
from test_diagnostic_context import state_for
from src.agents.diagnostic import diagnostic_agent_node


def test_fingerprint_ignores_review_metadata_but_tracks_inputs():
    state = state_for('chest pain')
    first = input_fingerprint(state)
    state['presentation']['diagnostic_review'] = {'status': 'CURRENT'}
    assert input_fingerprint(state) == first
    state['demographics'].allergies = ['new allergy']
    assert input_fingerprint(state) != first


def test_feedback_clears_outputs_and_restarts_triage():
    state = state_for('chest pain')
    state.update(diagnostic_agent_node(state))
    state.update(clinician_notes='headache', approved_by_clinician=True)
    result = feedback_processor_node(state)
    assert result['raw_notes'] == ['headache']
    assert result['urgency_resume_node'] == 'triage'
    for key in ('differentials', 'evidence', 'safety_flags', 'symbolic_overrides'):
        assert result[key] == []
    assert result['approved_by_clinician'] is False
    assert result['diagnostic_fingerprint'] is None


def test_api_reassessment_handoff_removes_old_persisted_results(client):
    path = start(client, decision('no_imaging'))
    before = client.get(path+'/results').json()
    assert before['differentials']
    assert before['presentation']['diagnostic_review']['status'] == 'CURRENT'
    response = client.post(path+'/reevaluate', json={'notes':'headache'})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'REQUIRES_CLINICIAN_ASSESSMENT'
    after = client.get(path+'/results').json()
    assert after['differentials'] == []
    assert after['evidence'] == []
    assert after['clinician_approval']['approved'] is False
    assert client.post(path+'/approve', json={}).status_code != 200


def test_api_unchanged_reassessment_replaces_evidence_and_can_approve(client):
    path = start(client, decision('no_imaging'))
    before = client.get(path+'/results').json()
    response = client.post(path+'/reevaluate', json={'notes':'chest pain'})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'WAITING_FOR_CLINICIAN_REVIEW'
    after = client.get(path+'/results').json()
    assert len(after['differentials']) == len(before['differentials'])
    assert len(after['evidence']) == len(before['evidence'])
    assert after['presentation']['diagnostic_review']['input_fingerprint'] != before['presentation']['diagnostic_review']['input_fingerprint']
    assert client.post(path+'/approve', json={'review_version':client.get(path+'/review').json()['review_version']}).status_code == 200


def test_api_rejects_changed_fingerprint_at_review(client, monkeypatch):
    path = start(client, decision('no_imaging'))
    monkeypatch.setattr('src.services.clinical_workflow.input_fingerprint', lambda state: 'changed')
    response = client.post(path+'/approve', json={})
    assert response.status_code == 409
    assert 'stale' in response.text


def test_api_reevaluation_limit_does_not_clear_current_results(client):
    path = start(client, decision('no_imaging'))
    for _ in range(2):
        assert client.post(path+'/reevaluate', json={'notes':'chest pain'}).status_code == 200
    before = client.get(path+'/results').json()
    assert client.post(path+'/reevaluate', json={'notes':'headache'}).status_code == 409
    assert client.get(path+'/results').json() == before
