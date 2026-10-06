from test_triage_foundation import client
from test_optional_imaging import start, decision


def setup_review(client):
    path = start(client, decision('no_imaging'))
    results = client.get(path+'/results').json()
    evidence = results['evidence'][0]
    payload = dict(claim_id=evidence['claim_id'],claim=evidence['claim'],document_id=evidence['document_id'],
        corpus_sha256=results['presentation']['evidence_review']['corpus_sha256'],
        passage_sha256=evidence['content_sha256'],
        diagnostic_fingerprint=results['presentation']['diagnostic_review']['input_fingerprint'],
        verdict='INSUFFICIENT_SUPPORT',rationale='Topic context alone does not establish the diagnosis.')
    return path, payload


def test_authenticated_review_persists_without_changing_retrieval_or_checkpoint(client):
    path,payload=setup_review(client)
    response=client.post(path+'/evidence-reviews',json=payload)
    assert response.status_code==200,response.text
    assert response.json()['reviewer']=='D'
    assert response.json()['reviewer_authenticated'] is True
    assert response.json()['clinical_approval'] is False
    assert client.get(path+'/evidence-reviews').json()[0]['status']=='CURRENT'
    result=client.get(path+'/results').json()
    assert result['presentation']['evidence_review']['clinician_reviews'][0]['rationale']==payload['rationale']
    assert result['evidence'][0]['support_status']=='RELATED_CONTEXT_ONLY'
    assert client.post(path+'/approve',json={'review_version':client.get(path+'/review').json()['review_version']}).status_code==200
    assert client.post(path+'/evidence-reviews',json=payload).status_code==409


def test_identity_cannot_be_forged_or_other_owner_used(client):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    path,payload=setup_review(client)
    assert client.post(path+'/evidence-reviews',json={**payload,'reviewer':'forged'}).status_code==422
    client.app.dependency_overrides[get_current_clinician]=lambda:DoctorModel(doctor_id='OTHER',full_name='Other',department='Test')
    assert client.post(path+'/evidence-reviews',json=payload).status_code==403
    assert client.get(path+'/evidence-reviews').status_code==403


def test_stale_claim_hash_and_source_are_rejected(client,monkeypatch,tmp_path):
    path,payload=setup_review(client)
    for key,value in [('claim','Changed'),('passage_sha256','0'*64),('diagnostic_fingerprint','0'*64),('corpus_sha256','0'*64)]:
        assert client.post(path+'/evidence-reviews',json={**payload,key:value}).status_code==409
    assert client.post(path+'/evidence-reviews',json=payload).status_code==200
    from src.core.evidence import CORPUS_PATH
    changed=tmp_path/'changed.json';changed.write_bytes(CORPUS_PATH.read_bytes()+b' ')
    monkeypatch.setattr('src.services.evidence_review.CORPUS_PATH',changed)
    assert client.get(path+'/evidence-reviews').json()[0]['status']=='STALE'
    assert client.post(path+'/evidence-reviews',json=payload).status_code==409


def test_revision_and_reevaluation(client):
    path,payload=setup_review(client)
    assert client.post(path+'/evidence-reviews',json=payload).status_code==200
    assert client.post(path+'/evidence-reviews',json={**payload,'verdict':'PARTIAL_SUPPORT','rationale':'Revised synthetic judgment'}).status_code==200
    assert [r['status'] for r in client.get(path+'/evidence-reviews').json()]==['SUPERSEDED','CURRENT']
    assert client.post(path+'/reevaluate',json={'notes':'chest pain'}).status_code==200
    assert client.get(path+'/evidence-reviews').json()==[]
    assert client.post(path+'/evidence-reviews',json=payload).status_code==409
    audit=client.get(path+'/audit-trail').json()
    assert any(r['action']=='EVIDENCE_JUDGMENT_RECORDED' for r in audit)


def test_invalid_verdict_and_blank_rationale_rejected(client):
    path,payload=setup_review(client)
    assert client.post(path+'/evidence-reviews',json={**payload,'verdict':'CONFIRMED_DIAGNOSIS'}).status_code==422
    assert client.post(path+'/evidence-reviews',json={**payload,'rationale':'   '}).status_code==422
    assert client.get('/api/clinical/sessions/absent/evidence-reviews').status_code==404


def test_missing_collection_marks_existing_judgment_stale(client,monkeypatch,tmp_path):
    path,payload=setup_review(client)
    assert client.post(path+'/evidence-reviews',json=payload).status_code==200
    monkeypatch.setattr('src.services.evidence_review.CORPUS_PATH',tmp_path/'missing.json')
    assert client.get(path+'/evidence-reviews').json()[0]['status']=='STALE'
    assert client.post(path+'/evidence-reviews',json=payload).status_code==409


def test_broader_offline_retrieval_regressions():
    from scripts.evaluate_evidence import evaluate
    report=evaluate()
    assert report['passed']==report['total']==10
    assert report['clinical_validation'] is False
    assert all(row['limitation'] for row in report['cases'] if row['id'] in ('synonym-gap','negated-topic-is-not-support'))
