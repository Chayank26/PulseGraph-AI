"""Bounded local passage retrieval. Topic relevance is not clinical support."""
import hashlib
import re
from datetime import date, datetime, timezone
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator
from src.core.state import ClinicalEvidence

CORPUS_PATH = Path(__file__).resolve().parents[1] / 'data' / 'evidence.json'


class Document(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    url: HttpUrl
    source_version: str = Field(min_length=1)
    verified_on: date
    review_due: date
    topics: list[str]
    passage: str = Field(min_length=1)

    @model_validator(mode='after')
    def dates(self):
        if self.review_due < self.verified_on:
            raise ValueError('Review date must follow verification')
        return self


class Corpus(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: str
    documents: list[Document]

    @model_validator(mode='after')
    def unique_ids(self):
        if len({doc.id for doc in self.documents}) != len(self.documents):
            raise ValueError('Duplicate document IDs')
        return self


def retrieve(candidates, path=CORPUS_PATH, today=None):
    today = today or datetime.now(timezone.utc).date()
    review = {'status': 'INSUFFICIENT_SUPPORT', 'method': 'local-topic-overlap-v1',
              'retrieved_at': datetime.now(timezone.utc).isoformat(), 'claims': [],
              'limitations': ['Topic matches do not establish a patient diagnosis or treatment indication.',
                             'Small local collection; no live search or automatic claim-support verification.']}
    try:
        raw = path.read_bytes()
        corpus = Corpus.model_validate_json(raw)
    except (OSError, ValueError):
        review.update(status='UNAVAILABLE', reason='Evidence collection could not be loaded or validated.')
        return [], review
    review.update(corpus_version=corpus.version, corpus_sha256=hashlib.sha256(raw).hexdigest())
    evidence = []
    for index, candidate in enumerate(candidates):
        query = set(re.findall(r'[a-z]+', candidate.condition_name.lower()))
        matches = []
        for doc in corpus.documents:
            overlap = query.intersection(doc.topics)
            if overlap:
                matches.append((len(overlap), doc.id, doc))
        matches.sort(key=lambda item: (-item[0], item[1]))
        usable = [doc for _, _, doc in matches if doc.verified_on <= today <= doc.review_due][:3]
        claim_id = f'candidate-{index}'
        review['claims'].append({'claim_id': claim_id, 'claim': candidate.condition_name,
            'status': 'RELATED_CONTEXT_ONLY' if usable else 'INSUFFICIENT_SUPPORT',
            'reason': 'No patient-specific entailment assessed.' if usable else
                      'Matching sources require review or are not yet verified.' if matches else 'No matching passage in this collection.',
            'document_ids': [doc.id for doc in usable]})
        for doc in usable:
            evidence.append(ClinicalEvidence(title=doc.title, source=doc.publisher,
                url_or_doi=str(doc.url), snippet=doc.passage,
                document_id=doc.id, claim_id=claim_id, claim=candidate.condition_name,
                support_status='RELATED_CONTEXT_ONLY', source_version=doc.source_version,
                verified_on=doc.verified_on.isoformat(), retrieved_at=review['retrieved_at'],
                content_sha256=hashlib.sha256(doc.passage.encode()).hexdigest()))
    if not candidates:
        review['status'] = 'NO_CANDIDATES'
    elif evidence:
        review['status'] = 'RELATED_CONTEXT_ONLY'
    return evidence, review
