import urllib.request
from src.agents.safety import safety_agent_node
from src.core.medication_review import history_fingerprint
from src.core.diagnostic import invalidate_diagnostics, input_fingerprint
from src.core.state import PatientDemographics
from src.tools.pharmacology import check_drug_safety_profile
from test_triage_foundation import client
from test_optional_imaging import start, decision


def test_no_network_and_explicit_limited_coverage(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Medication checks must not call external services')
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    state = {'demographics': PatientDemographics(patient_id='P', current_medications=['Unknown drug'], allergies=[])}
    state['medication_reconciliation'] = {'input_fingerprint':history_fingerprint(state['demographics']), 'medications':{'status':'recorded'}, 'allergies':{'status':'unknown'}}
    result = safety_agent_node(state)
    assert result['safety_flags'] == []
    review = result['presentation']['safety_review']
    assert review['interaction_provider'] == 'NOT_CONFIGURED'
    assert review['status'] == 'LIMITED_LOCAL_CHECKS'
    assert review['allergy_history'] == 'UNKNOWN'
    assert review['medication_history'] == 'RECORDED'
    assert result['audit_trail'][0].metadata['coverage'] == review


def test_blank_entries_do_not_create_allergy_matches():
    assert check_drug_safety_profile(['Amoxicillin', ' '], [' ', '']) == []


def test_local_alert_does_not_upgrade_coverage():
    demographics = PatientDemographics(patient_id='P', current_medications=['Amoxicillin'], allergies=['Penicillin'])
    result = safety_agent_node({'demographics':demographics, 'medication_reconciliation':{
        'input_fingerprint':history_fingerprint(demographics), 'medications':{'status':'recorded'}, 'allergies':{'status':'recorded'}}})
    assert result['safety_flags']
    assert result['presentation']['safety_review']['status'] == 'LIMITED_LOCAL_CHECKS'


def test_coverage_does_not_change_diagnostic_fingerprint_and_is_invalidated():
    state = {'presentation': {'chief_complaint':'chest pain'}}
    result = safety_agent_node(state)
    assert input_fingerprint(state) == input_fingerprint({**state, **result})
    assert 'safety_review' not in invalidate_diagnostics({**state, **result})['presentation']


def test_api_coverage_persists(client):
    path = start(client, decision('no_imaging'))
    result = client.get(path+'/results').json()
    assert result['presentation']['safety_review']['interaction_provider'] == 'NOT_CONFIGURED'
    assert result['presentation']['safety_review']['medication_history'] == 'NOT_RECORDED'
