import hashlib
from datetime import date
import pytest
from src.core.evidence import Corpus, CORPUS_PATH
from src.core.evidence_review import compare_corpora, ClaimReview, validate_claim_review, digest

TODAY = date(2026,10,5)


def test_updates_require_version_and_show_exact_diff():
    current = Corpus.model_validate_json(CORPUS_PATH.read_bytes())
    proposed = current.model_copy(deep=True)
    proposed.documents[0].passage = 'Changed passage'
    result = compare_corpora(current, proposed, TODAY)
    assert not result['valid']
    assert result['changes'][0]['before']['passage'] != result['changes'][0]['after']['passage']
    proposed.version = 'next'
    assert compare_corpora(current, proposed, TODAY)['valid']


def test_removed_sources_and_expiration_visible():
    current = Corpus.model_validate_json(CORPUS_PATH.read_bytes())
    proposed = current.model_copy(deep=True)
    proposed.documents.pop()
    proposed.version = 'next'
    assert compare_corpora(current, proposed, TODAY)['changes'][0]['action'] == 'removed'
    assert not compare_corpora(current, proposed, date(2027,2,1))['valid']


@pytest.mark.parametrize('verdict',['DIRECT_SUPPORT','PARTIAL_SUPPORT','CONFLICTING','INSUFFICIENT_SUPPORT'])
def test_review_is_bound_not_automatic_approval(verdict):
    raw=CORPUS_PATH.read_bytes()
    doc=Corpus.model_validate_json(raw).documents[0]
    review=ClaimReview(claim='Synthetic claim',document_id=doc.id,
        corpus_sha256=hashlib.sha256(raw).hexdigest(),passage_sha256=digest(doc.passage),
        verdict=verdict,rationale='Synthetic judgment for contract testing, not clinical annotation.',
        reviewer='test reviewer',reviewed_on=TODAY)
    result=validate_claim_review(review,raw,'Synthetic claim',TODAY)
    assert result['verdict']==verdict
    assert not result['clinical_approval']
    assert not result['reviewer_authenticated']
    with pytest.raises(ValueError):validate_claim_review(review,raw,'Changed claim',TODAY)
    with pytest.raises(ValueError):validate_claim_review(review,raw+b' ','Synthetic claim',TODAY)
    with pytest.raises(ValueError):validate_claim_review(review,raw,'Synthetic claim',date(2027,2,1))


def test_cli_does_not_modify_collection(tmp_path,monkeypatch,capsys):
    from scripts.review_evidence import main
    proposed=tmp_path/'proposed.json'
    raw=CORPUS_PATH.read_bytes();proposed.write_bytes(raw)
    monkeypatch.setattr('sys.argv',['review_evidence',str(proposed)])
    assert main()==0
    assert 'proposed_sha256' in capsys.readouterr().out
    assert proposed.read_bytes()==raw==CORPUS_PATH.read_bytes()
    proposed.write_text('{}')
    assert main()==1
