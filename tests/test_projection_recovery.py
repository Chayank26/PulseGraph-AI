from test_triage_foundation import client
from test_optional_imaging import start, decision
from src.services.clinical_workflow import ClinicalWorkflowService


def test_repeated_reconciliation_preserves_review_and_audit(client):
    path=start(client,decision('no_imaging'))
    before=client.get(path+'/review').json()
    audit=client.get(path+'/audit-trail').json()
    for _ in range(2):
        response=client.post(path+'/recover')
        assert response.status_code==200,response.text
        assert not response.json()['clinical_actions_replayed']
    assert client.get(path+'/review').json()['review_version']==before['review_version']
    assert client.get(path+'/audit-trail').json()==audit
    assert client.get(path+'/data-requests').json()==[]


def test_sync_failure_after_checkpoint_recovers_without_graph_replay(client, monkeypatch):
    original=ClinicalWorkflowService._sync_audit_and_results
    def fail(*args): raise RuntimeError('Injected projection failure')
    created=client.post('/api/clinical/sessions',json={'patient_id':'P'})
    path='/api/clinical/sessions/'+created.json()['session_id']
    monkeypatch.setattr(ClinicalWorkflowService,'_sync_audit_and_results',fail)
    assert client.post(path+'/run').status_code==500
    monkeypatch.setattr(ClinicalWorkflowService,'_sync_audit_and_results',original)
    assert client.post(path+'/recover').status_code==200
    pending=client.get(path+'/data-requests').json()
    assert pending
    assert client.post(path+'/recover').status_code==200
    assert [r['request_id'] for r in client.get(path+'/data-requests').json()]==[r['request_id'] for r in pending]


def test_resolved_request_never_reappears_after_recovery(client):
    created=client.post('/api/clinical/sessions',json={'patient_id':'P'})
    path='/api/clinical/sessions/'+created.json()['session_id']
    client.post(path+'/run')
    req=client.get(path+'/data-requests').json()[0]
    response={f['field_key']:'unknown' for f in req['required_fields']}
    assert client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':response}).status_code==200
    assert client.post(path+'/recover').status_code==200
    assert client.get(path+'/data-requests').json()==[]


def test_recovery_requires_owner(client):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    path=start(client,decision('no_imaging'))
    client.app.dependency_overrides[get_current_clinician]=lambda:DoctorModel(doctor_id='OTHER',full_name='Other',department='Test')
    assert client.post(path+'/recover').status_code==403


def test_interrupted_approval_is_not_replayed(client):
    from src.api.dependencies import get_db
    path=start(client,decision('no_imaging'))
    database=client.app.dependency_overrides[get_db](); db=next(database)
    try:
        service=ClinicalWorkflowService(db)
        session=service.sess_repo.get_by_session_id(path.rsplit('/',1)[1])
        service.graph.update_state({'configurable':{'thread_id':session.thread_id}},
            {'approved_by_clinician':True},as_node='symbolic_guardrail')
        before=client.get(path+'/results').json()
        assert client.post(path+'/recover').status_code==409
        assert client.get(path+'/results').json()==before
    finally:
        database.close()


def test_checkpoint_write_failure_does_not_consume_database_response(client, monkeypatch):
    import pytest
    from src.api.dependencies import get_db
    created=client.post('/api/clinical/sessions',json={'patient_id':'P'})
    path='/api/clinical/sessions/'+created.json()['session_id']
    client.post(path+'/run')
    before=client.get(path+'/data-requests').json()
    request=before[0]
    database=client.app.dependency_overrides[get_db](); db=next(database)
    try:
        service=ClinicalWorkflowService(db)
        def fail(*args, **kwargs): raise RuntimeError('Injected checkpoint write failure')
        monkeypatch.setattr(service.graph,'update_state',fail)
        with pytest.raises(RuntimeError):
            service.resolve_data_request(created.json()['session_id'],request['request_id'],
                {f['field_key']:'unknown' for f in request['required_fields']},reviewing_doctor_id='D')
        assert client.get(path+'/data-requests').json()==before
    finally:
        database.close()
