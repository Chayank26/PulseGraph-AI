"""Authenticated session-owner judgments; retrieval relevance remains unchanged."""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from src.core.evidence import CORPUS_PATH
from src.core.evidence_review import ClaimReview, validate_claim_review
from src.core.diagnostic import input_fingerprint
from src.core.state import AuditEntry
from src.services.session_lock import serialized_session
from src.services.clinical_workflow import ClinicalWorkflowService, WorkflowConflictError


class EvidenceReviewPayload(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    claim_id: str = Field(min_length=1, max_length=100)
    claim: str = Field(min_length=1, max_length=2000)
    document_id: str = Field(min_length=1, max_length=200)
    corpus_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    passage_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    diagnostic_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    verdict: Literal['DIRECT_SUPPORT', 'PARTIAL_SUPPORT', 'CONFLICTING', 'INSUFFICIENT_SUPPORT']
    rationale: str = Field(min_length=1, max_length=4000)


def current_claim(state, record):
    fingerprint = state.get('diagnostic_fingerprint')
    if not fingerprint or fingerprint != record['diagnostic_fingerprint'] or fingerprint != input_fingerprint(state):
        raise ValueError('Clinical inputs changed; reassessment is required.')
    expected_claims = {f'candidate-{i}': candidate.condition_name for i, candidate in enumerate(state.get('differentials', []))}
    if expected_claims.get(record['claim_id']) != record['claim']:
        raise ValueError('Diagnostic candidate changed.')
    evidence = next((item for item in state.get('evidence', [])
        if item.claim_id == record['claim_id'] and item.document_id == record['document_id']), None)
    if evidence is None or evidence.claim != record['claim'] or evidence.content_sha256 != record['passage_sha256']:
        raise ValueError('Retrieved claim or passage changed.')
    metadata = (state.get('presentation') or {}).get('evidence_review') or {}
    if metadata.get('corpus_sha256') != record['corpus_sha256']:
        raise ValueError('Retrieval collection changed.')
    return evidence.claim


class EvidenceReviewService:
    def __init__(self, db):
        self.workflow = ClinicalWorkflowService(db)

    def session(self, session_id, doctor_id):
        session = self.workflow.sess_repo.get_by_session_id(session_id)
        if session is None:
            raise LookupError('Session not found.')
        if session.doctor_id != doctor_id:
            raise PermissionError('Only the session owner may access evidence reviews.')
        config = {'configurable': {'thread_id': session.thread_id}}
        return session, config, self.workflow.graph.get_state(config)

    @serialized_session
    def submit(self, session_id, doctor_id, payload):
        session, config, snapshot = self.session(session_id, doctor_id)
        if snapshot.next != ('human_review',):
            raise WorkflowConflictError('Evidence judgments require the clinical review checkpoint.')
        record = payload.model_dump()
        now = datetime.now(timezone.utc)
        review = ClaimReview(claim=payload.claim, document_id=payload.document_id,
            corpus_sha256=payload.corpus_sha256, passage_sha256=payload.passage_sha256,
            verdict=payload.verdict, rationale=payload.rationale, reviewer=doctor_id,
            reviewed_on=now.date())
        try:
            claim = current_claim(snapshot.values, record)
            validate_claim_review(review, CORPUS_PATH.read_bytes(), claim, now.date())
        except (OSError, ValueError) as exc:
            raise WorkflowConflictError('Evidence review is stale or unavailable: '+str(exc)) from exc
        record.update(review.model_dump(mode='json'), review_id=str(uuid4()),
                      recorded_at=now.isoformat(), reviewer_authenticated=True,
                      clinical_approval=False)
        presentation = deepcopy(snapshot.values['presentation'])
        metadata = presentation['evidence_review']
        metadata.setdefault('clinician_reviews', []).append(record)
        self.workflow.graph.update_state(config, {'presentation': presentation,
            'approved_by_clinician': False,
            'audit_trail': [AuditEntry(agent_name='EvidenceReview', action='EVIDENCE_JUDGMENT_RECORDED',
                summary='Session owner recorded an evidence judgment; diagnostic support was not automatically upgraded.',
                metadata=record)]}, as_node='symbolic_guardrail')
        self.workflow._sync_audit_and_results(session, self.workflow.graph.get_state(config).values)
        return {**record, 'status': 'CURRENT'}

    def list(self, session_id, doctor_id):
        session, _, snapshot = self.session(session_id, doctor_id)
        saved = self.workflow.sess_repo.get_cds_result(session_id)
        metadata = ((saved.presentation if saved else {}) or {}).get('evidence_review') or {}
        records = deepcopy(metadata.get('clinician_reviews', []))
        latest = {(r['claim_id'], r['document_id']): r['review_id'] for r in records}
        for record in records:
            try:
                claim = current_claim(snapshot.values, record)
                validate_claim_review(ClaimReview.model_validate({k:record[k] for k in ClaimReview.model_fields}),
                    CORPUS_PATH.read_bytes(), claim, datetime.now(timezone.utc).date())
                record['status'] = ('CURRENT' if latest[(record['claim_id'],record['document_id'])] == record['review_id'] else 'SUPERSEDED')
            except (OSError, ValueError, KeyError) as exc:
                record.update(status='STALE', stale_reason=str(exc))
        return records
