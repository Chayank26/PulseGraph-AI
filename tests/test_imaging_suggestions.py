import json
import pytest
from src.core.differential import Proposal
from src.core.data_requests import validate_response
from src.core.imaging_suggestions import suggestion_request
from test_triage_foundation import client
from test_optional_imaging import start, decision, resolve
from differential_fixture import SyntheticProvider


class ImagingProvider(SyntheticProvider):
    def generate(self, payload, schema):
        result = json.loads(super().generate(payload, schema))
        if result['candidates']:
            candidate = result['candidates'][0]
            result['imaging_suggestion'] = dict(candidate_name=candidate['condition_name'],
                modality='CT', anatomy='chest', assessment_question='Synthetic assessment question',
                evidence_ids=candidate['evidence_ids'])
        return json.dumps(result)


@pytest.mark.parametrize('action', ['reject', 'optional', 'required', 'uncertain'])
def test_api_explicit_review_and_no_repeat(client, monkeypatch, action):
    monkeypatch.setattr('src.agents.diagnostic.configured_provider', lambda: ImagingProvider())
    path = start(client, decision('no_imaging'))
    req, = client.get(path+'/data-requests').json()
    assert req['pathway_name'] == 'Model imaging suggestion'
    assert client.post(path+'/approve', json={}).status_code != 200
    response = resolve(client, path, {'imaging_suggestion_action': action,
        'imaging_suggestion_reason': 'Synthetic clinician judgment'})
    assert response.status_code == 200, response.text
    if action == 'required':
        req, = client.get(path+'/data-requests').json()
        assert req['pathway_name'] == 'Required imaging report'
        response = resolve(client, path, {'imaging_action':'submit_report', 'imaging_report':'Synthetic report'})
        assert response.status_code == 200, response.text
    assert client.get(path+'/data-requests').json() == []
    expected = 'REQUIRES_CLINICIAN_ASSESSMENT' if action == 'uncertain' else 'WAITING_FOR_CLINICIAN_REVIEW'
    assert response.json()['status'] == expected
    audit = client.get(path+'/audit-trail').json()
    assert any(row['action'] == 'IMAGING_SUGGESTION_REVIEW_REQUESTED' for row in audit)


def proposal():
    candidate = dict(condition_name='Synthetic', supporting_ids=['f'], contradicting_ids=[], missing_ids=[], evidence_ids=['e'])
    return dict(outcome='candidates', reason='candidate_review', candidates=[candidate],
        imaging_suggestion=dict(candidate_name='Synthetic', modality='CT', anatomy='chest',
            assessment_question='Question', evidence_ids=['e']))


@pytest.mark.parametrize('change', [{'candidate_name':'Other'}, {'evidence_ids':['unknown']}, {'assessment_question':''}])
def test_invalid_bindings_rejected(change):
    data = proposal(); data['imaging_suggestion'].update(change)
    with pytest.raises(ValueError): Proposal.model_validate(data)


@pytest.mark.parametrize('reason', ['', ' ', '__unknown__', '__unavailable__', 1])
def test_written_reason_required(reason):
    request = suggestion_request(Proposal.model_validate(proposal()).imaging_suggestion)
    assert not validate_response(request, {'imaging_suggestion_action':'required', 'imaging_suggestion_reason':reason})[0]


def test_review_requires_session_owner(client, monkeypatch):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    monkeypatch.setattr('src.agents.diagnostic.configured_provider', lambda: ImagingProvider())
    path = start(client, decision('no_imaging'))
    client.app.dependency_overrides[get_current_clinician] = lambda: DoctorModel(doctor_id='OTHER',full_name='Other',department='Test')
    assert resolve(client, path, {'imaging_suggestion_action':'required', 'imaging_suggestion_reason':'Reason'}).status_code == 400
