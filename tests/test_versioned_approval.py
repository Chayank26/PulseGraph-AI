from test_triage_foundation import client
from test_optional_imaging import start, decision
from test_authenticated_evidence import setup_review


def test_version_required_and_recorded(client):
    path=start(client,decision('no_imaging'))
    package=client.get(path+'/review').json()
    assert package['can_approve']
    assert client.get(path+'/review').json()['review_version']==package['review_version']
    assert client.post(path+'/approve',json={}).status_code==409
    response=client.post(path+'/approve',json={'review_version':package['review_version'],'notes':'Reviewed'})
    assert response.status_code==200,response.text
    saved=client.get(path+'/results').json()['clinician_approval']
    assert saved['record']['review_version']==package['review_version']
    assert saved['record']['doctor_id']=='D'
    assert saved['record']['approved_at']
    assert client.post(path+'/approve',json={'review_version':package['review_version']}).status_code!=200


def test_evidence_judgment_invalidates_displayed_version(client):
    path,payload=setup_review(client)
    old=client.get(path+'/review').json()['review_version']
    assert client.post(path+'/evidence-reviews',json=payload).status_code==200
    new=client.get(path+'/review').json()['review_version']
    assert new!=old
    assert client.post(path+'/approve',json={'review_version':old}).status_code==409
    assert client.post(path+'/approve',json={'review_version':new}).status_code==200


def test_other_owner_cannot_read_or_approve(client):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    path=start(client,decision('no_imaging'))
    version=client.get(path+'/review').json()['review_version']
    client.app.dependency_overrides[get_current_clinician]=lambda:DoctorModel(doctor_id='OTHER',full_name='Other',department='Test')
    assert client.post(path+'/reject',json={}).status_code==403
    assert client.post(path+'/reevaluate',json={'notes':'test'}).status_code==403
    assert client.get(path+'/review').status_code==403
    assert client.post(path+'/approve',json={'review_version':version}).status_code==403


def test_reassessment_changes_version(client):
    path=start(client,decision('no_imaging'))
    version=client.get(path+'/review').json()['review_version']
    assert client.post(path+'/reevaluate',json={'notes':'chest pain'}).status_code==200
    assert client.post(path+'/approve',json={'review_version':version}).status_code==409
