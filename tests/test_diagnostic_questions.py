import json
import pytest
from src.core.diagnostic_questions import plan_questions
from src.core.state import DiagnosticDifferential, VitalSigns
from src.core.data_requests import validate_response, apply_response_to_state, resolve_request
from test_triage_foundation import client
from test_optional_imaging import start, decision
from differential_fixture import SyntheticProvider


def candidate(missing):
    return DiagnosticDifferential(condition_name='Synthetic candidate', likelihood='Not estimated',rationale='test',missing_information=missing)


def request():
    return plan_questions({},[candidate(['spo2_percent'])])[0]


def test_known_values_dedup_and_bounded_fields():
    req,_=plan_questions({'vitals':VitalSigns(spo2_percent=98)},[candidate(['spo2_percent','bmi','temperature_c','heart_rate_bpm','respiratory_rate','bmi'])])
    assert len(req.optional_fields)==3
    assert 'spo2_percent' not in [f.field_key for f in req.optional_fields]
    assert all(f.description and not f.required for f in req.optional_fields)
    assert plan_questions({'pending_data_requests':[req]},[candidate(['spo2_percent'])])[0] is None


@pytest.mark.parametrize('answer',['__unknown__','__unavailable__'])
def test_unknown_and_unavailable_preserved_without_measurements_or_repetition(answer):
    req=request();response={'diagnostic_followup_action':'provide_values','spo2_percent':answer}
    assert validate_response(req,response)[0]
    updates=apply_response_to_state({},response)
    assert not updates.get('vitals')
    assert updates['diagnostic_followup_answers']['spo2_percent']==answer
    state={**updates,'resolved_data_requests':[resolve_request(req,response)]}
    assert plan_questions(state,[candidate(['spo2_percent'])])[0] is None


@pytest.mark.parametrize('value',[True,-1,101,'NaN','',None])
def test_invalid_optional_measurements_are_rejected(value):
    assert not validate_response(request(),{'diagnostic_followup_action':'provide_values','spo2_percent':value})[0]


def test_continue_and_session_round_limit():
    response={'diagnostic_followup_action':'proceed_to_review'}
    assert validate_response(request(),response)[0]
    assert plan_questions(apply_response_to_state({},response),[candidate(['spo2_percent'])])[0] is None
    assert plan_questions({'diagnostic_followup_rounds':2},[candidate(['spo2_percent'])])[1]=='clarification_limit_reached'
    assert not validate_response(request(),{**response,'spo2_percent':98})[0]
    assert not validate_response(request(),{**response,'age':50})[0]


class QuestionProvider(SyntheticProvider):
    def generate(self,payload,schema):
        result=json.loads(super().generate(payload,schema))
        for candidate in result['candidates']:
            candidate['missing_ids']=[key for key in ['spo2_percent'] if key in payload['missing_ids']]
        return json.dumps(result)


@pytest.mark.parametrize('answer',[98,'__unknown__','__unavailable__'])
def test_api_resumption_preserves_answer_and_does_not_repeat(client,monkeypatch,answer):
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:QuestionProvider())
    path=start(client,decision('no_imaging'))
    req,=client.get(path+'/data-requests').json()
    assert req['requesting_agent']=='diagnostic'
    response=client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{
        'diagnostic_followup_action':'provide_values','spo2_percent':answer}})
    assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_FOR_CLINICIAN_REVIEW'
    assert client.get(path+'/data-requests').json()==[]
    audit=client.get(path+'/audit-trail').json()
    assert any(row['action']=='DIAGNOSTIC_CLARIFICATION_REQUESTED' for row in audit)


def test_api_clinician_can_continue_without_values(client,monkeypatch):
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:QuestionProvider())
    path=start(client,decision('no_imaging'))
    req,=client.get(path+'/data-requests').json()
    response=client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{'diagnostic_followup_action':'proceed_to_review'}})
    assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_FOR_CLINICIAN_REVIEW'
    assert client.get(path+'/results').json()['presentation']['diagnostic_review']['generation']['clarification_status']=='clinician_directed_review'


def test_api_two_round_cap_survives_full_resumption(client,monkeypatch):
    class ManyQuestions(SyntheticProvider):
        def generate(self,payload,schema):
            result=json.loads(super().generate(payload,schema))
            for candidate in result['candidates']:candidate['missing_ids']=payload['missing_ids']
            return json.dumps(result)
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:ManyQuestions())
    path=start(client,decision('no_imaging'))
    values={'blood_pressure_sys':120,'blood_pressure_dia':80,'bmi':24,'heart_rate_bpm':80,
            'respiratory_rate':18,'spo2_percent':98,'temperature_c':37}
    asked=set()
    for _ in range(2):
        req,=client.get(path+'/data-requests').json()
        fields=[f['field_key'] for f in req['optional_fields']]
        assert len(fields)<=3 and not asked.intersection(fields)
        asked.update(fields)
        result=client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{
            'diagnostic_followup_action':'provide_values',**{k:values[k] for k in fields}}})
        assert result.status_code==200,result.text
    assert result.json()['status']=='WAITING_FOR_CLINICIAN_REVIEW'
    assert client.get(path+'/data-requests').json()==[]
    assert client.get(path+'/results').json()['presentation']['diagnostic_review']['generation']['clarification_status']=='clarification_limit_reached'


def test_api_urgency_rechecked_before_diagnostic_continuation(client,monkeypatch):
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:QuestionProvider())
    client.put('/api/patients/P',json={'chief_complaint':'chest pain'})
    created=client.post('/api/clinical/sessions',json={'patient_id':'P',
        'raw_notes':[f'[ACQUIRED CLINICAL DATA]: {k} = {v}' for k,v in {
            'history_score':0,'ecg_score':0,'troponin_score':0,'cardiac_risk_factors_count':0,'atherosclerotic_disease':'false'}.items()],
        'pathway_decisions':{'heart':'applicable'}, 'imaging_decision':decision('no_imaging'),
        'urgency_context':{'pregnant':False,'clinician_concern':False,'new_confusion':False,'oxygen_scale':'standard'}})
    path='/api/clinical/sessions/'+created.json()['session_id']
    assert client.post(path+'/run').status_code==200
    req,=client.get(path+'/data-requests').json()
    assert req['requesting_agent']=='diagnostic'
    response=client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{
        'diagnostic_followup_action':'provide_values','spo2_percent':80}})
    assert response.status_code==200,response.text
    pending=client.get(path+'/data-requests').json()
    assert pending[0]['requesting_agent']=='urgency_check'
    assert client.get(path+'/results').json()['differentials']==[]
    assert client.post(path+'/approve',json={}).status_code!=200


def test_diagnostic_response_requires_session_owner(client,monkeypatch):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:QuestionProvider())
    path=start(client,decision('no_imaging'))
    req,=client.get(path+'/data-requests').json()
    client.app.dependency_overrides[get_current_clinician]=lambda:DoctorModel(doctor_id='OTHER',full_name='Other',department='Test')
    assert client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{'diagnostic_followup_action':'proceed_to_review'}}).status_code==400
