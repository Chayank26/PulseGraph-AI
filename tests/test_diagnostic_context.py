import pytest
from langgraph.graph import StateGraph, START, END
from src.agents.diagnostic import diagnostic_agent_node
from src.core.diagnostic import build_diagnostic_context
from src.core.presentation import extract_presentation
from src.core.state import ClinicalState, PatientDemographics, ImagingData, ImagingFinding


def state_for(text):
    return {'demographics': PatientDemographics(patient_id='test', chief_complaint=text),
            'presentation': extract_presentation(text, []).model_dump(mode='json'),
            'raw_notes': [], 'risk_scores': [], 'differentials': [], 'audit_trail': []}


@pytest.mark.parametrize('text', ['No chest pain', 'Previous chest pain', 'Father has chest pain',
                                  'Possible chest pain', 'Chest pain. No chest pain',
                                  'No shortness of breath', 'History of dyspnea'])
def test_non_current_assertions_do_not_activate_candidates(text):
    assert diagnostic_agent_node(state_for(text))['differentials'] == []


def test_positive_paraphrase_has_only_actual_source_evidence():
    state = state_for('pain in my chest')
    result = diagnostic_agent_node(state)
    candidate, = result['differentials']
    assert candidate.likelihood == 'Not estimated'
    assert candidate.supporting_evidence == ['chief_complaint[0:16]: pain in my chest']
    assert candidate.recommended_workup == []
    assert candidate.icd10_code is None


def test_history_and_legacy_imaging_do_not_invent_findings():
    state = state_for('No chest pain')
    state['demographics'].chronic_conditions = ['hypertension', 'hyperlipidemia']
    state['imaging_data'] = ImagingData(image_path='cardiomegaly.png', findings=[
        ImagingFinding(finding_name='Cardiomegaly', confidence=0.99)])
    assert diagnostic_agent_node(state)['differentials'] == []


def test_saved_context_is_authoritative_over_raw_keyword_notes():
    state = state_for('No chest pain')
    state['raw_notes'] = ['[Clinician feedback] consider heart disease and dyspnea']
    assert diagnostic_agent_node(state)['differentials'] == []


def test_context_preserves_unknowns_history_and_report_without_parsing():
    state = state_for('chest pain and blurred vision')
    state['demographics'].allergies = ['penicillin']
    state['demographics'].current_medications = ['example medication']
    state['presentation']['imaging_plan'] = {'status': 'REPORT_PROVIDED', 'report': 'No pleural effusion.'}
    context = build_diagnostic_context(state)
    assert context.presentation.imaging_plan['report'] == 'No pleural effusion.'
    assert context.demographics.allergies == ['penicillin']
    assert context.demographics.current_medications == ['example medication']
    assert 'spo2_percent' in context.missing_observations
    assert context.presentation.unrecognized_fragments
    assert any('Uninterpreted' in item for item in context.limitations)
    assert diagnostic_agent_node(state)['differentials'] == []
    assert diagnostic_agent_node(state)['presentation']['diagnostic_review']['generation']['reason'] == 'outside_scope'


@pytest.mark.parametrize('status', ['SKIPPED', 'WAITING_FOR_REPORT', 'OVERRIDDEN', 'REQUIRES_CLINICIAN_ASSESSMENT'])
def test_missing_imaging_is_not_normal(status):
    state = state_for('chest pain')
    state['presentation']['imaging_plan'] = {'status': status}
    context = build_diagnostic_context(state)
    assert any('missing imaging is not a normal result' in item for item in context.limitations)


def test_legacy_intake_fallback_still_respects_negation():
    state = state_for('No chest pain')
    del state['presentation']
    assert diagnostic_agent_node(state)['differentials'] == []
    assert any('No completed triage' in item for item in build_diagnostic_context(state).limitations)


def test_real_graph_replaces_previous_candidates_including_empty_result():
    builder = StateGraph(ClinicalState)
    builder.add_node('diagnostic', diagnostic_agent_node)
    builder.add_edge(START, 'diagnostic')
    builder.add_edge('diagnostic', END)
    graph = builder.compile()
    first = graph.invoke(state_for('chest pain'))
    assert len(first['differentials']) == 1
    second = graph.invoke(first)
    assert len(second['differentials']) == 1
    second['presentation'] = extract_presentation('No chest pain', []).model_dump(mode='json')
    assert graph.invoke(second)['differentials'] == []


@pytest.fixture(autouse=True)
def synthetic_model(monkeypatch):
    from differential_fixture import install
    install(monkeypatch)
