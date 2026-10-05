"""Offline source-update and claim-review contracts; no automatic clinical approval."""
import hashlib
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from src.core.evidence import Corpus


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def compare_corpora(current: Corpus, proposed: Corpus, today: date):
    old = {d.id: d for d in current.documents}
    new = {d.id: d for d in proposed.documents}
    changes = []
    errors = []
    for key in sorted(old.keys() | new.keys()):
        before, after = old.get(key), new.get(key)
        if before == after:
            continue
        changes.append({'document_id': key, 'action': 'added' if before is None else 'removed' if after is None else 'changed',
                        'before': before.model_dump(mode='json') if before else None,
                        'after': after.model_dump(mode='json') if after else None})
    if changes and current.version == proposed.version:
        errors.append('Changed content requires a new corpus version.')
    for doc in proposed.documents:
        if doc.url.scheme != 'https':
            errors.append(f'{doc.id}: HTTPS source required.')
        if not doc.verified_on <= today <= doc.review_due:
            errors.append(f'{doc.id}: outside verification/review interval.')
        if not doc.topics or any(not token.isalpha() or token != token.lower() for token in doc.topics):
            errors.append(f'{doc.id}: topics must be lowercase alphabetic tokens.')
    return {'valid': not errors, 'errors': errors, 'changes': changes,
            'current_version': current.version, 'proposed_version': proposed.version,
            'clinical_approval': False,
            'limitations': ['Schema checks cannot verify source authenticity, licensing or clinical correctness.',
                           'Review every changed passage and URL against the original source before committing.']}


class ClaimReview(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    claim: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    corpus_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    passage_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    verdict: Literal['DIRECT_SUPPORT', 'PARTIAL_SUPPORT', 'CONFLICTING', 'INSUFFICIENT_SUPPORT']
    rationale: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    reviewed_on: date


def validate_claim_review(review: ClaimReview, corpus_bytes: bytes, claim: str, today: date):
    """Bind a recorded human judgment to exact inputs; never infer entailment."""
    if review.claim != claim:
        raise ValueError('Claim changed; review is stale.')
    if review.corpus_sha256 != hashlib.sha256(corpus_bytes).hexdigest():
        raise ValueError('Corpus changed; review is stale.')
    corpus = Corpus.model_validate_json(corpus_bytes)
    doc = next((d for d in corpus.documents if d.id == review.document_id), None)
    if doc is None or digest(doc.passage) != review.passage_sha256:
        raise ValueError('Passage missing or changed.')
    if not doc.verified_on <= review.reviewed_on <= today <= doc.review_due:
        raise ValueError('Review or source dates are not current.')
    return {'status': 'RECORDED_REVIEW', 'verdict': review.verdict,
            'reviewer_authenticated': False, 'clinical_approval': False}
