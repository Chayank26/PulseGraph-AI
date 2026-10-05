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
    limitations: list[str] = Field(default_factory=list)


def build_diagnostic_context(state) -> DiagnosticContext:
    demographics = state.get('demographics')
    saved = state.get('presentation')
    presentation = (ClinicalPresentation.model_validate(saved) if saved else
        extract_presentation(getattr(demographics, 'chief_complaint', '') or '', state.get('raw_notes', [])))
    vitals = state.get('vitals')
    limitations = list(presentation.limitations)
    limitations.append('Legacy candidate rules are not a validated diagnostic model; likelihood is not estimated.')
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
        limitations=limitations)
