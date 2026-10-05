from datetime import date
from pathlib import Path
from src.core.evidence import retrieve, CORPUS_PATH
from src.core.state import DiagnosticDifferential
from src.agents.evidence_rag import evidence_rag_agent_node
from src.core.diagnostic import input_fingerprint, invalidate_diagnostics
from test_diagnostic_context import state_for
from test_triage_foundation import client


def candidate(name):
    return DiagnosticDifferential(condition_name=name, likelihood='Not estimated', rationale='test')


def test_passages_are_traceable_not_probabilities_or_diagnostic_support():
    results, review = retrieve([candidate('Pulmonary Embolism')], today=date(2026,10,5))
    assert len(results) == 1
    assert results[0].document_id == 'nice-ng158-1.1.17'
    assert results[0].relevance_score is None
    assert results[0].support_status == 'RELATED_CONTEXT_ONLY'
    assert len(results[0].content_sha256) == 64
    assert review['corpus_sha256']
    assert review['claims'][0]['document_ids'] == [results[0].document_id]


def test_missing_irrelevant_expired_and_future_collections(tmp_path):
    result, review = retrieve([candidate('Pulmonary Embolism')], path=tmp_path/'missing')
    assert result == [] and review['status'] == 'UNAVAILABLE'
    path=tmp_path/'bad.json'; path.write_text('{}')
    assert retrieve([],path=path)[1]['status'] == 'UNAVAILABLE'
    for day in [date(2026,10,4),date(2027,1,4)]:
        result, review = retrieve([candidate('Pulmonary Embolism')],today=day)
        assert result == []
        assert review['claims'][0]['status'] == 'INSUFFICIENT_SUPPORT'
    assert retrieve([candidate('Migraine')])[1]['status'] == 'INSUFFICIENT_SUPPORT'
    assert retrieve([])[1]['status'] == 'NO_CANDIDATES'


def test_duplicate_document_ids_rejected(tmp_path):
    import json
    corpus=json.loads(CORPUS_PATH.read_text())
    corpus['documents'].append(corpus['documents'][0])
    path=tmp_path/'duplicate.json';path.write_text(json.dumps(corpus))
    assert retrieve([],path=path)[1]['status'] == 'UNAVAILABLE'


def test_mixed_claims_keep_unsupported_candidate_visible():
    _, review=retrieve([candidate('Pulmonary Embolism'),candidate('Migraine')],today=date(2026,10,5))
    assert [c['status'] for c in review['claims']] == ['RELATED_CONTEXT_ONLY','INSUFFICIENT_SUPPORT']


def test_evidence_metadata_does_not_change_input_fingerprint_and_invalidates():
    state=state_for('chest pain')
    state['differentials']=[candidate('Acute Coronary Syndrome / NSTEMI')]
    result=evidence_rag_agent_node(state)
    assert input_fingerprint(state)==input_fingerprint({**state,**result})
    assert invalidate_diagnostics({**state,**result})['presentation']['evidence_review']['status']=='STALE'


def test_api_persists_retrieval_provenance_and_preserves_approval(client):
    from test_optional_imaging import start, decision
    path=start(client,decision('no_imaging'))
    result=client.get(path+'/results').json()
    assert result['presentation']['evidence_review']['corpus_sha256']
    assert result['evidence'][0]['source_version']
    assert result['evidence'][0]['support_status']=='RELATED_CONTEXT_ONLY'
    assert client.post(path+'/approve',json={}).status_code==200
