"""Retrieve traceable local passages without asserting diagnostic validation."""
from src.core.state import AuditEntry
from src.core.evidence import retrieve


def evidence_rag_agent_node(state):
    evidence, review = retrieve(state.get('differentials', []))
    presentation = dict(state.get('presentation') or {})
    presentation['evidence_review'] = review
    return {'evidence': evidence, 'presentation': presentation,
        'audit_trail': [AuditEntry(agent_name='EvidenceRAGAgent', action='EVIDENCE_RETRIEVAL',
            summary=f"Local passage retrieval: {review['status']}; {len(evidence)} passages.", metadata=review)],
        'current_step': 'evidence_retrieved'}
