"""Conservative, bounded symptom extraction. Not a diagnosis or urgency classifier."""
import re
from src.core.routing import RoutingPlan
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceText(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: str
    text: str


class SymptomMention(BaseModel):
    model_config = ConfigDict(extra='forbid')
    symptom: str
    status: Literal['present', 'absent', 'historical', 'uncertain', 'other_person']
    source_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str
    context: str
    time_course: str | None = None
    severity: str | None = None
    location: str | None = None


class SymptomSummary(BaseModel):
    symptom: str
    status: Literal['present', 'absent', 'historical', 'uncertain', 'other_person', 'conflicting']
    mentions: list[SymptomMention]
    clarification_source: str | None = None


class UnrecognizedFragment(BaseModel):
    source_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str


class ClinicalPresentation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    evidence_review: dict | None = None
    symbolic_review: dict | None = None
    diagnostic_review: dict | None = None
    imaging_plan: dict | None = None
    routing: RoutingPlan | None = None
    extractor_version: str = 'rules-v2'
    unrecognized_fragments: list[UnrecognizedFragment] = Field(default_factory=list)
    sources: list[SourceText]
    symptoms: list[SymptomSummary]
    unrecognized_sources: list[str]
    limitations: list[str] = Field(default_factory=lambda: [
        'Only explicitly recognized phrases are extracted; omitted symptoms remain unknown.',
        'Negation and timing rules cover a limited set of English phrases; clinician review is required.',
        'This summary does not establish diagnosis, urgency, or imaging need.',
    ])

    @model_validator(mode='after')
    def validate_sources(self):
        sources = {source.source_id: source.text for source in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError('Source identifiers must be unique')
        for symptom in self.symptoms:
            if not symptom.mentions:
                raise ValueError('Each symptom requires source evidence')
            for mention in symptom.mentions:
                text = sources.get(mention.source_id)
                if (text is None or mention.end <= mention.start or
                        text[mention.start:mention.end] != mention.quote or
                        mention.context not in text or mention.symptom != symptom.symptom):
                    raise ValueError('Symptom evidence must match the supplied source text')
                for detail in (mention.time_course, mention.severity, mention.location):
                    if detail is not None and detail not in mention.context:
                        raise ValueError('Extracted attributes must be copied from source context')
        for fragment in self.unrecognized_fragments:
            text = sources.get(fragment.source_id)
            if text is None or fragment.end <= fragment.start or text[fragment.start:fragment.end] != fragment.quote:
                raise ValueError('Unrecognized fragments must match the supplied source text')
        if any(source not in sources for source in self.unrecognized_sources):
            raise ValueError('Unrecognized source references must exist')
        return self


# Extraction vocabulary is independent of the currently available calculators.
SYMPTOMS = {
    'chest_pain': r'chest pain|chest discomfort|chest tightness|pain in (?:my |the |his |her )?chest|(?:my |the )?chest hurts',
    'breathlessness': r'shortness of breath|dyspn(?:ea|oea)|breathlessness|difficulty breathing',
    'leg_swelling': r'leg swelling|swollen leg(?:s)?',
    'dvt': r'dvt|deep vein thrombosis',
    'abdominal_pain': r'abdominal pain|stomach pain|belly pain|pain in (?:my |the |his |her )?(?:abdomen|stomach|belly)',
    'headache': r'headache(?:s)?',
    'fever': r'fever|febrile',
    'cough': r'cough(?:ing)?',
    'vomiting': r'vomiting|vomit(?:s|ed)?',
    'diarrhea': r'diarrh(?:ea|oea)',
    'dizziness': r'dizziness|dizzy|lightheadedness',
    'weakness': r'weakness',
    'rash': r'rash',
    'back_pain': r'back pain|pain in (?:my |the |his |her )?back',
    'dysuria': r'dysuria|painful urination',
    'injury': r'injury|injuries|trauma',
}
PATTERNS = {key: re.compile(r'\b(?:' + pattern + r')\b', re.I) for key, pattern in SYMPTOMS.items()}
BOUNDARY = re.compile(r'[.!?;\n]|\b(?:but|however|although|yet)\b', re.I)
CUES = re.compile(
    r'\b(?P<other>family history of|mother has|father has|sister has|brother has)\b'
    r'|\b(?P<uncertain>possible|possibly|suspected|uncertain|unclear|rule out|cannot rule out|not sure|may have|if|monitor for)\b'
    r'|\b(?P<historical>history of|previous(?:ly)?|prior|past|resolved)\b'
    r'|\b(?P<absent>no|denies|denied|without|negative for|not experiencing)\b'
    r'|\b(?P<present>reports|has|experiencing|developed|now|currently|presents with)\b', re.I)
TIME = re.compile(r'\b(?:since\s+(?:yesterday|today|this morning|last night)|for\s+\d+\s+(?:minutes?|hours?|days?|weeks?|months?|years?)|sudden onset|acute|chronic)\b', re.I)
LOCATION = re.compile(r'\b(?:left|right|bilateral|upper|lower)(?:[- ](?:left|right|upper|lower))?\b', re.I)
SEVERITY = re.compile(r'\b(?:mild|moderate|severe|\d{1,2}/10)\b', re.I)


def _status(prefix: str, suffix: str) -> str:
    cues = list(CUES.finditer(prefix))
    status = cues[-1].lastgroup if cues else 'present'
    if status == 'other':
        return 'other_person'
    if re.match(r'\s*(?:is )?present\b', suffix, re.I):
        return 'present'
    if re.match(r'\s*(?:is |was )?(?:denied|absent|not present)\b', suffix, re.I):
        return 'absent'
    if re.match(r'\s*(?:has |is |was )?resolved\b', suffix, re.I):
        return 'historical'
    if re.search(r'\b\d+\s+(?:days?|weeks?|months?|years?) ago\b', suffix, re.I):
        return 'historical'
    return status


# Only discard known grammar/attributes, never an open-ended trailing phrase.
# Remaining narrative is a coverage gap, not a new symptom or a negative finding.
NEUTRAL = re.compile(
    r"\b(?:patient|presents|presenting|with|reports|reporting|complains|complaint|symptoms?|"
    r"of|in|the|a|an|my|his|her|and|or|also|has|have|had|is|was|are|were|"
    r"episode|episodes|started|began|today|yesterday|currently|now|experiencing|"
    r"present|absent|denied|not|resolved|for|since)\b", re.I)
STRUCTURED_VALUE = re.compile(r"\b[a-z_]+=(?:[^\s,;]+)", re.I)


def _has_unparsed_text(clause: str) -> bool:
    residual = clause
    for pattern in [*PATTERNS.values(), TIME, LOCATION, SEVERITY, CUES, STRUCTURED_VALUE, NEUTRAL]:
        residual = pattern.sub(' ', residual)
    return bool(re.search(r"[a-zA-Z]", residual))


def extract_presentation(complaint: str, notes: list[str]) -> ClinicalPresentation:
    sources = [SourceText(source_id='chief_complaint', text=complaint)] if complaint.strip() else []
    # Structured answers and generated administrative/history notes are not symptom assertions.
    for i, note in enumerate(notes):
        if note.strip() and not note.lstrip().lower().startswith(('[', 'allergies:', 'conditions:', 'medications:')):
            sources.append(SourceText(source_id=f'raw_notes[{i}]', text=note))
    mentions: dict[str, list[SymptomMention]] = {}
    unmatched = []
    fragments = []
    for source in sources:
        found = False
        start = 0
        for boundary in [*BOUNDARY.finditer(source.text), None]:
            end = boundary.start() if boundary else len(source.text)
            clause = source.text[start:end]
            hits = sorted((match.start(), key, match) for key, pattern in PATTERNS.items() for match in pattern.finditer(clause))
            for _, key, match in hits:
                found = True
                time = TIME.search(clause) if len(hits) == 1 else None
                severity = SEVERITY.search(clause) if len(hits) == 1 else None
                location = LOCATION.search(clause) if len(hits) == 1 else None
                mention = SymptomMention(symptom=key, status=_status(clause[:match.start()], clause[match.end():]),
                    source_id=source.source_id, start=start + match.start(), end=start + match.end(),
                    quote=match.group(), context=clause.strip(),
                    time_course=time.group() if time else None, severity=severity.group() if severity else None, location=location.group() if location else None)
                mentions.setdefault(key, []).append(mention)
            if _has_unparsed_text(clause):
                left = len(clause) - len(clause.lstrip())
                right = len(clause.rstrip())
                fragments.append(UnrecognizedFragment(source_id=source.source_id,
                    start=start + left, end=start + right, quote=clause[left:right]))
            start = boundary.end() if boundary else end
        if not found:
            unmatched.append(source.source_id)
    symptoms = []
    for key, evidence in mentions.items():
        statuses = {m.status for m in evidence}
        if {'present', 'absent'} <= statuses:
            status = 'conflicting'
        else:
            status = next(s for s in ('present', 'uncertain', 'absent', 'historical', 'other_person') if s in statuses)
        symptoms.append(SymptomSummary(symptom=key, status=status, mentions=evidence))
    return ClinicalPresentation(sources=sources, symptoms=symptoms, unrecognized_sources=unmatched, unrecognized_fragments=fragments)
