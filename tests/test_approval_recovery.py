import pytest
from src.api.dependencies import get_db
from src.core.state import ClinicianIdentity
from src.services.clinical_workflow import ClinicalWorkflowService
from test_triage_foundation import client
from test_optional_imaging import start, decision


def interrupt(client, monkeypatch, boundary='human_review'):
    path=start(client,decision('no_imaging'))
    old=client.get(path+'/review').json()['review_version']
    database=client.app.dependency_overrides[get_db](); db=next(database)
    try:
        service=ClinicalWorkflowService(db)
        def fail(*args, **kwargs): raise RuntimeError('Injected approval interruption')
        monkeypatch.setattr(service.graph,'invoke',fail)
        with pytest.raises(RuntimeError):
            service.approve_session(path.rsplit('/',1)[1],ClinicianIdentity(doctor_id='D',full_name='Test',department='Test'),review_version=old)
        if boundary=='ehr_export':
            session=service.sess_repo.get_by_session_id(path.rsplit('/',1)[1])
            service.graph.update_state({'configurable':{'thread_id':session.thread_id}},
                {'current_step':'clinician_approved'},as_node='human_review')
    finally: database.close()
    return path,old


@pytest.mark.parametrize('boundary',['human_review','ehr_export'])
def test_interrupted_approval_requires_new_review(client,monkeypatch,boundary):
    path,old=interrupt(client,monkeypatch,boundary)
    before=client.get(path+'/review').json()
    assert before['recovery_required'] and not before['can_approve']
    assert client.post(path+'/approve',json={'review_version':before['review_version']}).status_code==409
    recovered=client.post(path+'/recover')
    assert recovered.status_code==200,recovered.text
    assert recovered.json()['recovery']=='FRESH_REVIEW_REQUIRED'
    assert recovered.json()['clinical_actions_replayed'] is False
    after=client.get(path+'/review').json()
    assert after['can_approve'] and not after['recovery_required']
    assert after['review_version'] not in (old,before['review_version'])
    assert after['approval'] is None
    assert client.post(path+'/approve',json={'review_version':old}).status_code==409
    assert client.post(path+'/recover').status_code==200
    assert client.get(path+'/review').json()['review_version']==after['review_version']
    audit=client.get(path+'/audit-trail').json()
    resets=[row for row in audit if row['action']=='INTERRUPTED_APPROVAL_RESET']
    assert len(resets)==1
    assert resets[0]['metadata_json']['prior_approval']['review_version']==old
    assert not any(row['action']=='EHR_PACKAGE_EXPORT' for row in audit)
    assert client.post(path+'/approve',json={'review_version':after['review_version']}).status_code==200


def test_retry_after_projection_failure_does_not_reset_twice(client,monkeypatch):
    path,_=interrupt(client,monkeypatch)
    database=client.app.dependency_overrides[get_db](); db=next(database)
    try:
        service=ClinicalWorkflowService(db)
        def fail(*args, **kwargs): raise RuntimeError('Injected recovery projection failure')
        monkeypatch.setattr(service,'_sync_audit_and_results',fail)
        with pytest.raises(RuntimeError):service.recover_session(path.rsplit('/',1)[1],'D')
    finally:database.close()
    version=client.get(path+'/review').json()['review_version']
    assert client.post(path+'/recover').status_code==200
    assert client.get(path+'/review').json()['review_version']==version
    assert sum(row['action']=='INTERRUPTED_APPROVAL_RESET' for row in client.get(path+'/audit-trail').json())==1


def test_completed_approval_is_not_reset(client):
    path=start(client,decision('no_imaging'))
    version=client.get(path+'/review').json()['review_version']
    client.post(path+'/approve',json={'review_version':version})
    assert client.post(path+'/recover').json()['status']=='APPROVED'
    assert client.get(path+'/results').json()['clinician_approval']['approved'] is True
