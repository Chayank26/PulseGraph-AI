"""Clinician-confirmed imaging policy; no autonomous indication or pixel inference."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImagingDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, strict=True)
    decision: Literal['no_imaging', 'optional', 'required', 'uncertain']
    assessment_question: str | None = Field(default=None, min_length=1, max_length=2000)
    reason: str = Field(min_length=1, max_length=2000)
    modality: str | None = Field(default=None, min_length=1, max_length=100)
    anatomy: str | None = Field(default=None, min_length=1, max_length=200)
    report: str | None = Field(default=None, min_length=1, max_length=20000)
    study_reference: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode='after')
    def study_details(self):
        if self.assessment_question in ("__unavailable__", "__unknown__"):
            raise ValueError("Write an assessment question or choose clinician assessment instead.")
        if self.reason == "__unavailable__":
            raise ValueError("A written clinical rationale is required.")
        if (self.decision == 'required' or self.report) and not (self.modality and self.anatomy):
            raise ValueError('Specify the modality and body region for required imaging or a supplied report.')
        if self.decision in ('no_imaging', 'uncertain') and self.report:
            raise ValueError('Choose optional or required to include an existing report.')
        return self


def decision_from_response(data):
    return ImagingDecision.model_validate({key: (None if data.get('imaging_' + key) == '' else data.get('imaging_' + key))
        for key in ImagingDecision.model_fields})


def assessment_fingerprint(state):
    """Bind required study intent to intake and observations, not generated output."""
    import hashlib
    import json
    from src.core.presentation import extract_presentation
    demographics = state.get('demographics')
    presentation = extract_presentation(getattr(demographics, 'chief_complaint', '') or '', state.get('raw_notes', []))
    inputs = {'demographics': demographics.model_dump(mode='json') if demographics else None,
              'sources': [source.model_dump() for source in presentation.sources],
              'vitals': state['vitals'].model_dump() if state.get('vitals') else None,
              'risk_scores': [{k:v for k,v in score.model_dump(mode='json').items() if k != 'calculated_at'} for score in state.get('risk_scores', [])],
              'pathway_decisions': state.get('pathway_decisions'),
              'urgency_context': state.get('urgency_context')}
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
