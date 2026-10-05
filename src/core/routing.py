"""Presentation grouping and explicit calculator applicability; not diagnosis."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Decision = Literal['applicable', 'not_applicable', 'unknown']
UNAVAILABLE = '__unavailable__'


class PathwayDecisions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    heart: Decision | None = None
    curb65: Decision | None = None
    wells: Decision | None = None


class PathwayDefinition(BaseModel):
    key: str
    name: str
    symptoms: set[str]
    covered_symptoms: set[str]
    applicability: str
    required_fields: set[str]
    score_name: str
    source: str


PATHWAYS = [
    PathwayDefinition(key='heart', name='HEART Score Assessment', symptoms={'chest_pain'}, covered_symptoms={'chest_pain'},
        applicability='Clinician confirms this adult acute chest-pain presentation is suitable for the HEART assessment in an emergency-care context; exclusions and urgent alternatives have been considered.',
        required_fields={'history_score','ecg_score','troponin_score','cardiac_risk_factors_count'}, score_name='HEART Score',
        source='https://www.acc.org/latest-in-cardiology/ten-points-to-remember/2022/10/10/23/15/2022-acc-expert-consensus-on-chest-pain'),
    PathwayDefinition(key='curb65', name='CURB-65 Pneumonia Assessment', symptoms={'breathlessness','cough'}, covered_symptoms={'breathlessness','cough','fever'},
        applicability='Clinician has made a diagnosis of community-acquired pneumonia in this adult in hospital and confirms CURB-65 is appropriate. Breathlessness alone is insufficient.',
        required_fields={'confusion','bun_mg_dl','respiratory_rate','blood_pressure_sys','blood_pressure_dia'}, score_name='CURB-65 Score',
        source='https://www.nice.org.uk/guidance/ng250/chapter/Recommendations'),
    PathwayDefinition(key='wells', name='Wells PE Assessment', symptoms={'breathlessness','leg_swelling','dvt'}, covered_symptoms={'breathlessness','leg_swelling','dvt'},
        applicability='Clinician suspects pulmonary embolism in this adult and confirms this assessment is appropriate. A symptom or elevated pulse alone does not establish suspected PE.',
        required_fields={'heart_rate_gt_100','pe_most_likely','clinical_signs_dvt','immobilization_surgery','previous_dvt_pe','hemoptysis','malignancy'}, score_name='Wells Score (PE)',
        source='https://www.nice.org.uk/guidance/ng158/chapter/Recommendations'),
]
GROUPS = {
    'cardiovascular': {'chest_pain'}, 'respiratory': {'breathlessness','cough'},
    'vascular': {'leg_swelling','dvt'}, 'gastrointestinal': {'abdominal_pain','vomiting','diarrhea'},
    'neurological': {'headache','dizziness','weakness'}, 'skin': {'rash'},
    'urinary': {'dysuria'}, 'musculoskeletal_or_injury': {'back_pain','injury'}, 'systemic': {'fever'},
}


class PathwayStatus(BaseModel):
    key: str
    name: str
    status: Literal['NEEDS_CONFIRMATION','READY','NEEDS_DATA','COMPLETE','NOT_APPLICABLE','UNSUPPORTED','INCOMPLETE']
    rationale: str
    source: str
    unavailable_fields: list[str] = Field(default_factory=list)


class RoutingPlan(BaseModel):
    groups: dict[str, list[str]]
    pathways: list[PathwayStatus]
    handoff_reasons: list[str]
    requires_clinician_assessment: bool
    limitations: list[str] = Field(default_factory=lambda: [
        'Presentation groups are descriptive, not diagnoses.',
        'Only the listed calculators are implemented; no score establishes low risk.',
        'Applicability requires clinician judgement. This router is not clinically validated.',
    ])


def plan_routing(state, presentation, acquired) -> RoutingPlan:
    present = {s.symptom for s in presentation.symptoms if s.status == 'present'}
    groups = {name: sorted(present & symptoms) for name, symptoms in GROUPS.items() if present & symptoms}
    uncertain = [s.symptom for s in presentation.symptoms if s.status in ('uncertain','conflicting')]
    reasons = [f'Uncertain presentation requires clinician assessment: {", ".join(uncertain)}.'] if uncertain else []
    for fragment in presentation.unrecognized_fragments:
        reasons.append(f'Uninterpreted text requires clinician assessment ({fragment.source_id}): {fragment.quote}')
    demographics = state.get('demographics')
    age = demographics.age if demographics else None
    excluded = age is not None and age < 18 or (state.get('urgency_context') or {}).get('pregnant') is True
    pathways = []
    covered = set()
    initial = PathwayDecisions.model_validate(state.get('pathway_decisions') or {}).model_dump()
    for definition in PATHWAYS:
        candidate = bool(present & definition.symptoms)
        decision = acquired.get(f'pathway_decision_{definition.key}', initial.get(definition.key))
        status = 'NOT_APPLICABLE'
        rationale = 'No matching current symptom in the bounded extraction vocabulary.'
        unavailable = sorted(k for k in definition.required_fields if acquired.get(k) == UNAVAILABLE)
        if candidate:
            rationale = definition.applicability
            if excluded:
                status = 'UNSUPPORTED'
                reasons.append(f'{definition.name}: pediatric/pregnancy assessment is outside the implemented scope.')
            elif decision is None:
                status = 'NEEDS_CONFIRMATION'
            elif decision == 'unknown':
                status = 'INCOMPLETE'
                reasons.append(f'{definition.name}: applicability is unknown.')
            elif decision == 'not_applicable':
                rationale = 'Clinician marked this assessment not applicable.'
            elif decision == 'applicable':
                if unavailable:
                    status = 'INCOMPLETE'
                    reasons.append(f'{definition.name}: unavailable data ({", ".join(unavailable)}).')
                else:
                    status = 'READY'
                    covered |= definition.covered_symptoms
            else:
                status = 'INCOMPLETE'
                reasons.append(f'{definition.name}: invalid applicability decision.')
        pathways.append(PathwayStatus(key=definition.key, name=definition.name, status=status,
            rationale=rationale, source=definition.source, unavailable_fields=unavailable))
    pending_coverage = set().union(*(d.covered_symptoms for d in PATHWAYS
        if any(p.key == d.key and p.status == 'NEEDS_CONFIRMATION' for p in pathways)))
    uncovered = present - covered - pending_coverage
    if uncovered:
        reasons.append(f'No selected automated assessment covers: {", ".join(sorted(uncovered))}.')
    if not present:
        reasons.append('No confirmed current presentation matches an implemented assessment; clinician assessment is required.')
    elif not covered and not any(p.status == 'NEEDS_CONFIRMATION' for p in pathways):
        reasons.append('No applicable, complete automated assessment is available for this presentation.')
    return RoutingPlan(groups=groups, pathways=pathways, handoff_reasons=reasons,
                       requires_clinician_assessment=bool(reasons))
