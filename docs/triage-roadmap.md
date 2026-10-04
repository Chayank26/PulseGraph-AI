# General triage roadmap

Each phase ends with verification, a review of uncommitted changes, and a suggested
commit message. Stop before starting the next phase. Do not commit automatically.

1. **Reliable intake and score display.** Persist session notes and structured
   vitals; consume the saved complaint; validate numeric/boolean/enum inputs;
   reuse acquired data; align displayed scores with backend results. Preserve
   existing clinical formulas and routing in this phase.
2. **Structured symptom understanding.** Extract symptoms, time course, explicit
   denials, unknowns, conflicts, and source references into validated structured
   output. Evaluate an LLM-assisted extraction boundary with deterministic validation.
3. **Urgency assessment.** Introduce clinician-reviewed escalation rules and
   uncertainty handling before questionnaires, with reassessment as inputs change.
4. **General pathway routing and questions.** Add applicability/exclusion checks,
   multiple concerns, explicit unsupported presentations, and targeted questions.
5. **Optional imaging.** Define no-imaging, optional, assessment-dependent, and
   uncertain decisions; clinician confirmation/override; conditional execution.
6. **Evaluation and expansion.** Evaluate synthetic presentation groups, routing,
   questions, escalation, unsupported cases, and conflicts before adding pathways.

## Phase 1 deployment

Apply `DEBUG=false venv/bin/alembic upgrade head` before restarting the API.
Existing sessions have nullable intake data and continue to accept run inputs.
New sessions persist notes, vitals and image path; empty run requests reuse them.
The run endpoint accepts a JSON object; legacy notes-array bodies are also accepted.
No urgency rules, clinical score thresholds, or imaging-routing decisions change.

## Phase 2: structured presentation

Implemented a bounded deterministic English extractor with a validated
`ClinicalPresentation` schema, exact text offsets, source quotes, contextual
assertion status, and conservative time/severity/location extraction. Multiple
symptoms are represented separately. When a clause mentions multiple symptoms,
attributes are left unknown instead of being assigned to the wrong symptom.

The vocabulary includes cardiopulmonary and non-cardiopulmonary terms. Only
current positive assertions activate existing symptom-driven calculators.
Historical, denied, family-member, and uncertain mentions remain visible without
being treated as confirmed current symptoms. Conflicting positive/negative
statements pause triage for clinician clarification; the original evidence is
retained. Unrecognized input is retained for review, never translated into a
normal finding. This is not general-purpose clinical NLP: unhandled wording,
complex temporal relationships, abbreviations, and partial recognition still
need clinician review. Existing downstream diagnostic keyword logic is unchanged.

Results and review APIs expose the persisted presentation, and the triage UI
shows statements and source context. Apply `DEBUG=false venv/bin/alembic upgrade
head` before restarting the backend for the new nullable results column.

### LLM boundary evaluation

No model call or new provider dependency is enabled in this phase. A future
extractor should consume only the supplied source texts and produce the same
schema. Quote spans and extracted attributes must validate against those texts.
Grounded quotes alone do not prove correct assertion interpretation: a model
adapter needs an evaluated corpus, negation/temporality/conflict checks,
clinician review, and explicit failure/unknown behavior before it can affect
routing. Unknown facts must never be silently inferred. This bounded rule-based
implementation supplies the initial comparison baseline, not an LLM substitute
claiming unrestricted symptom understanding.

Urgency classification, pathway expansion, and optional imaging remain later
phases. The imaging step still follows the existing workflow in this phase.

## Phase 3: urgency screening and reassessment

A dedicated `urgency_check` graph node runs before triage, after every resolved
clinical data request, and before clinician-requested diagnostic reevaluation.
It persists the latest assessment and records assessment snapshots in the audit
trail. Urgent findings pause routine questionnaires for explicit review by the
session's authenticated clinician. Acknowledgement allows assessment continuation;
it does not clear the alert or attest that the patient is safe. Approval cannot
bypass a pending data/urgency checkpoint. Changed observations or configuration
invalidate prior acknowledgement. No external emergency notification is sent.

The versioned candidate screen uses individual extreme observation thresholds
in the RCP NEWS2 report (chart 1, printed page 29), plus explicit clinician concern
consistent with NICE CG50 recommendation 1.4. It is **not a NEWS2 calculation**,
does not aggregate scores, and does not assign disposition or treatment.

Sources:
- https://www.rcp.ac.uk/media/a4ibkkbf/news2-final-report_0_0.pdf
- https://www.nice.org.uk/guidance/CG50/chapter/recommendations

### Scope and configuration

Physiological rules require recorded age >=16 and explicit non-pregnancy.
SpO2 screening additionally requires a clinician-confirmed standard scale;
individualized targets require manual assessment. Explicit clinician concern
triggers review regardless of these restrictions. Unrecorded applicability is
never inferred. Missing values and unsupported populations remain visibly
incomplete/outside scope. Measurement age and clinical trends are not evaluated.
No detected trigger must never be read as low risk. Several moderately abnormal
observations may require escalation without triggering this limited screen.

`URGENCY_RULES` accepts a JSON configuration matching `UrgencyRules`, including
thresholds, version, `reviewed_by`, and `review_reference`. Defaults are marked
`PENDING_CLINICAL_REVIEW`: implementation/testing is not clinical validation.
Before clinical use, obtain local clinical review of population, thresholds,
escalation procedures, and response staffing. Recording review metadata is an
administrative record, not independent verification. Changed local thresholds
must have their own version and clinical review; default source references do
not endorse local modifications.

New session intake accepts optional `urgency_context` fields: clinician concern,
new confusion, pregnancy, and oxygen scale. Unknown values remain unknown. The
intake UI collects these explicitly. Older/direct workspace sessions without
context show the scope limitation instead of a false normal result. Acquired
confusion and vital measurements trigger reassessment. Symptom-driven emergency
classification, pediatric/obstetric rules, full NEWS2, and automatic escalation
notifications are not implemented in this phase.

Apply `DEBUG=false venv/bin/alembic upgrade head` before restarting the backend.
