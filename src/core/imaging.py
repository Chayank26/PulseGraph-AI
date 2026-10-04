"""Clinician-confirmed imaging policy; no autonomous indication or pixel inference."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImagingDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, strict=True)
    decision: Literal['no_imaging', 'optional', 'required', 'uncertain']
    reason: str = Field(min_length=1, max_length=2000)
    modality: str | None = Field(default=None, min_length=1, max_length=100)
    anatomy: str | None = Field(default=None, min_length=1, max_length=200)
    report: str | None = Field(default=None, min_length=1, max_length=20000)
    study_reference: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode='after')
    def study_details(self):
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
