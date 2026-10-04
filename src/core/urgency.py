"""Limited adult observation screen; not NEWS2 or a disposition decision."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

SOURCE = 'https://www.rcp.ac.uk/media/a4ibkkbf/news2-final-report_0_0.pdf'


class UrgencyContext(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    clinician_concern: bool | None = None
    new_confusion: bool | None = None
    pregnant: bool | None = None
    oxygen_scale: Literal['standard', 'individualized', 'unknown'] = 'unknown'


class UrgencyRules(BaseModel):
    """Candidate rules requiring local clinical review before clinical deployment."""
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    version: str = 'adult-observation-screen-v1'
    reviewed_by: str | None = None
    review_reference: str | None = None
    heart_rate_low: float = Field(default=40, ge=0)
    heart_rate_high: float = Field(default=131, gt=0)
    respiratory_rate_low: float = Field(default=8, ge=0)
    respiratory_rate_high: float = Field(default=25, gt=0)
    systolic_low: float = Field(default=90, ge=0)
    systolic_high: float = Field(default=220, gt=0)
    temperature_low: float = Field(default=35, ge=0)
    spo2_low: float = Field(default=91, ge=0, le=100)

    @model_validator(mode='after')
    def ordered_thresholds(self):
        for low, high in [(self.heart_rate_low, self.heart_rate_high),
                          (self.respiratory_rate_low, self.respiratory_rate_high),
                          (self.systolic_low, self.systolic_high)]:
            if low >= high:
                raise ValueError('Urgency lower thresholds must be below upper thresholds')
        return self


class UrgencyReason(BaseModel):
    rule_id: str
    field: str
    value: float | bool
    explanation: str
    source: str


class UrgencyAssessment(BaseModel):
    status: Literal['URGENT_REVIEW', 'INCOMPLETE', 'OUTSIDE_SCOPE', 'NO_TRIGGER_DETECTED']
    assessed_at: str
    rules_version: str
    rules_review_status: Literal['PENDING_CLINICAL_REVIEW', 'REVIEW_RECORDED']
    review_reference: str | None
    reasons: list[UrgencyReason]
    missing_information: list[str]
    limitations: list[str]
    fingerprint: str
    acknowledged: bool = False
    action: str


def assess_urgency(state, rules: UrgencyRules | None = None) -> UrgencyAssessment:
    rules = rules or UrgencyRules()
    context = UrgencyContext.model_validate(state.get('urgency_context') or {})
    demographics = state.get('demographics')
    age = demographics.age if demographics else None
    vitals = state.get('vitals')
    observations = vitals.model_dump() if vitals else {}
    reasons = []
    missing = []
    for field in ('clinician_concern', 'new_confusion', 'pregnant'):
        if getattr(context, field) is None:
            missing.append(field)
    if age is None:
        missing.append('age')
    fields = ('heart_rate_bpm', 'respiratory_rate', 'blood_pressure_sys', 'temperature_c', 'spo2_percent')
    missing.extend(field for field in fields if observations.get(field) is None)
    if context.oxygen_scale != 'standard':
        missing.append('standard oxygen scale applicability (SpO2 rule not evaluated)')
    limitations = [
        'Limited observation screen, not a NEWS2 score or comprehensive urgency assessment.',
        'No trigger does not establish low risk or suitability for discharge.',
        'Measurement freshness and clinical trajectory have not been verified.',
    ]
    def add(rule_id, field, value, explanation, source=SOURCE):
        reasons.append(UrgencyReason(rule_id=rule_id, field=field, value=value, explanation=explanation, source=source))
    if context.clinician_concern is True:
        add('CLINICIAN_CONCERN', 'clinician_concern', True, 'Clinician has explicitly reported an urgent concern.',
            'https://www.nice.org.uk/guidance/CG50/chapter/recommendations')
    supported = age is not None and age >= 16 and context.pregnant is False
    if supported:
        if context.new_confusion is True:
            add('NEW_CONFUSION', 'new_confusion', True, 'New confusion explicitly reported.')
        for field, low, high, unit in [
            ('heart_rate_bpm', rules.heart_rate_low, rules.heart_rate_high, 'bpm'),
            ('respiratory_rate', rules.respiratory_rate_low, rules.respiratory_rate_high, 'breaths/min'),
            ('blood_pressure_sys', rules.systolic_low, rules.systolic_high, 'mmHg'),
            ('temperature_c', rules.temperature_low, None, '°C'),
            ('spo2_percent', rules.spo2_low, None, '%'),
        ]:
            value = observations.get(field)
            if value is None or (field == 'spo2_percent' and context.oxygen_scale != 'standard'):
                continue
            if value <= low or (high is not None and value >= high):
                threshold = f'≤ {low}' if value <= low else f'≥ {high}'
                add(field.upper(), field, value, f'{field.replace("_", " ")}: {value} {unit}; trigger {threshold} {unit}.')
    else:
        limitations.append('Adult vital-sign rules were not applied: age ≥16 and explicit non-pregnancy are required. Obtain clinician assessment.')
    status = 'URGENT_REVIEW' if reasons else ('OUTSIDE_SCOPE' if not supported else ('INCOMPLETE' if missing else 'NO_TRIGGER_DETECTED'))
    digest = hashlib.sha256(json.dumps({'age': age, 'vitals': observations,
        'observation_revision': state.get('urgency_observation_revision', 0),
        'context': context.model_dump(), 'rules': rules.model_dump()}, sort_keys=True).encode()).hexdigest()[:20]
    key = f'urgency_review_{digest}'
    acknowledged = any(r.status == 'RESOLVED' and r.requesting_agent == 'urgency_check'
                       and any(f.field_key == key for f in r.required_fields)
                       and (r.clinician_response or {}).get(key) is True
                       for r in state.get('resolved_data_requests', []))
    return UrgencyAssessment(status=status, assessed_at=datetime.now(timezone.utc).isoformat(),
        rules_version=rules.version, rules_review_status='REVIEW_RECORDED' if rules.reviewed_by and rules.review_reference else 'PENDING_CLINICAL_REVIEW',
        review_reference=rules.review_reference, reasons=reasons, missing_information=missing,
        limitations=limitations, fingerprint=digest, acknowledged=acknowledged,
        action='Prompt clinician review required; do not wait for questionnaires or imaging.' if reasons else 'Clinician assessment remains necessary; this screen does not establish low risk.')
