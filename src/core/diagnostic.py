"""Structured diagnostic context; no inference from raw report text or history."""
from pydantic import BaseModel, Field
from src.core.presentation import ClinicalPresentation, extract_presentation
from src.core.state import PatientDemographics, VitalSigns, RiskScore


class DiagnosticContext(BaseModel):
    presentation: ClinicalPresentation
    demographics: PatientDemographics | None = None
    vitals: VitalSigns | None = None
    risk_scores: list[RiskScore] = Field(default_factory=list)
    pathway_decisions: dict = Field(default_factory=dict)
    missing_observations: list[str] = Field(default_factory=list)
    followup_answers: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


def build_diagnostic_context(state) -> DiagnosticContext:
    demographics = state.get('demographics')
    saved = state.get('presentation')
    presentation = (ClinicalPresentation.model_validate(saved) if saved else
        extract_presentation(getattr(demographics, 'chief_complaint', '') or '', state.get('raw_notes', [])))
    vitals = state.get('vitals')
    limitations = list(presentation.limitations)
    limitations.append('Differential proposals are not clinically validated; likelihood is not estimated.')
    if not saved:
        limitations.append('No completed triage presentation was available; context was extracted from intake.')
    plan = presentation.imaging_plan or {}
    if plan.get('status') == 'REPORT_PROVIDED':
        limitations.append('Supplied imaging report is retained verbatim and has not been interpreted by this agent.')
    else:
        limitations.append('No interpreted imaging evidence is available; missing imaging is not a normal result.')
    if presentation.unrecognized_fragments:
        limitations.append('Uninterpreted narrative requires clinician assessment.')
    if presentation.routing:
        limitations.extend(presentation.routing.handoff_reasons)
    return DiagnosticContext(presentation=presentation, demographics=demographics, vitals=vitals,
        risk_scores=state.get('risk_scores', []), pathway_decisions=state.get('pathway_decisions') or {},
        missing_observations=[key for key in VitalSigns.model_fields if getattr(vitals, key, None) is None],
        followup_answers=state.get('diagnostic_followup_answers') or {}, limitations=limitations)


def input_fingerprint(state):
    """Stable fingerprint of clinical inputs, excluding generated output timestamps."""
    import hashlib
    import json
    def encode(value):
        if hasattr(value, 'model_dump'):
            return value.model_dump(mode='json')
        raise TypeError(type(value).__name__)
    inputs = {key: state.get(key) for key in (
        'demographics', 'raw_notes', 'vitals', 'pathway_decisions',
        'imaging_decision', 'imaging_response', 'image_path', 'urgency_context',
        'diagnostic_followup_answers', 'diagnostic_followup_disposition')}
    inputs['presentation'] = {k: v for k, v in (state.get('presentation') or {}).items() if k not in ('diagnostic_review', 'symbolic_review', 'evidence_review', 'safety_review')}
    inputs['risk_scores'] = [{k: v for k, v in encode(score).items() if k != 'calculated_at'} for score in state.get('risk_scores', [])]
    return hashlib.sha256(json.dumps(inputs, default=encode, sort_keys=True).encode()).hexdigest()


def invalidate_diagnostics(state):
    presentation = dict(state.get('presentation') or {})
    presentation.pop('safety_review', None)
    if presentation:
        presentation['evidence_review'] = {'status': 'STALE', 'claims': [], 'limitations': ['Reassessment required.']}
        presentation['diagnostic_review'] = {'status': 'STALE', 'limitations': ['Inputs changed; reassessment is required.']}
    return {'differentials': [], 'evidence': [], 'safety_flags': [], 'symbolic_overrides': [],
            'approved_by_clinician': False, 'diagnostic_fingerprint': None,
            'presentation': presentation or None}
