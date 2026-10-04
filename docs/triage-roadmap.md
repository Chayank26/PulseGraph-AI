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

## Phase 4: presentation routing and targeted questions

Presentation groups now include cardiovascular, respiratory, vascular,
gastrointestinal, neurological, skin, urinary, musculoskeletal/injury, and
systemic complaints. Multiple groups are retained. These are descriptive
categories, not diagnoses or newly implemented treatment pathways.

Calculator applicability is explicitly confirmed by the clinician. Relevant
candidate assessments are grouped into one request with `applicable`,
`not_applicable`, or `unknown` answers. No answer is preselected. In API workflows,
validated `pathway_decisions` can be supplied at session creation or execution.
A high pulse alone no longer activates Wells questions. Decisions are recorded
with session input or acquired answers and reflected in persisted routing output.

Applicability references:
- HEART: adult acute chest-pain assessment in an emergency-care context:
  https://www.acc.org/latest-in-cardiology/ten-points-to-remember/2022/10/10/23/15/2022-acc-expert-consensus-on-chest-pain
- CURB-65: clinician-diagnosed adult community-acquired pneumonia in hospital:
  https://www.nice.org.uk/guidance/ng250/chapter/Recommendations
- Wells PE: clinician-suspected PE, not dyspnea or tachycardia alone:
  https://www.nice.org.uk/guidance/ng158/chapter/Recommendations

This implementation conservatively limits calculator routing to age >=18 and
excludes known pregnancy. These are software coverage limits, not statements
about every tool's validated population. Confirmation includes consideration of
clinical exclusions; it is not an exhaustive automated exclusion check. Existing
calculator formulas/interpretations remain unchanged (including the current
Wells interpretation); this is not a full implementation of the cited clinical
management guidelines. Local clinical validation remains necessary.

Only selected tools ask for missing inputs. Triage fields may explicitly allow
`__unavailable__`; this never becomes a normal number or a false boolean.
Unavailable fields mark the affected assessment incomplete and stop repeated
requests. Other selected assessments can finish, with their scores preserved.
Urgency review cannot be bypassed with the unavailable option.

Unsupported, uncertain, excluded, declined-all, and incomplete presentations
produce an explicit `REQUIRES_CLINICIAN_ASSESSMENT` handoff when supported work is
finished. The graph ends before imaging/diagnosis in these cases, and the UI
stops polling and displays the handoff. Successful completion of a supported
calculator does not imply coverage of an additional unsupported complaint.
Current scores replace prior triage-pass scores to avoid retaining stale results.

Routing is persisted within the presentation JSON and exposed in results/review
responses. No database migration is required for this phase. Supported complete
assessments still use the existing downstream workflow; conditional imaging is
Phase 5. New clinical pathways and expanded extraction vocabulary remain later
work, rather than fabricated assessments for currently unsupported groups.

A second `/run` on an already-started session returns HTTP 409, preserving its
pending requests instead of duplicating them. Continue via data resolution or
clinician review; create a new session for a new assessment. The UI disables the
initial run action after startup and does not restart the graph after reevaluation.

## Phase 5: optional imaging and report review

The imaging stage now collects an explicit clinician decision: `no_imaging`,
`optional`, `required`, or `uncertain`, with a written rationale. The decision
request shows saved complaint/symptom context and allergies in the UI. This is a
clinician-confirmed policy, not a new autonomous imaging-indication model.
Symptoms and calculator scores do not independently order imaging.

No-imaging and optional-without-report decisions continue directly to diagnostic
processing. An optional existing report can be included with modality and body
region. Required imaging specifies modality and anatomy and pauses for a report;
a path alone does not satisfy that requirement. The clinician can submit the
report, explicitly mark it unavailable, document an override to proceed without
it, or request manual assessment. Unknown indication and unavailable required
reports produce `REQUIRES_CLINICIAN_ASSESSMENT`, not endless requests. Urgency
review still runs first and after data resolution, and cannot be bypassed by an
imaging decision or supplied report.

`imaging_decision` is accepted on session creation/run and persists in intake.
It uses `decision`, `reason`, and optional `modality`, `anatomy`, `report`, and
`study_reference`. Required studies and supplied reports require modality and
anatomy. Runtime decisions and report requests use the existing acquisition
endpoint. Only the session clinician can start the workflow or resolve imaging
requests. Unexpected imaging response fields and missing override reasons are
rejected. The resulting `presentation.imaging_plan` persists through the existing
results JSON and is available in results/review APIs. No migration is needed.

The live imaging node no longer calls the legacy filename demonstration. It
retains clinician-supplied report text without inventing structured findings or
confidence values. Reports remain structured rather than entering raw notes
consumed by the old diagnostic keyword rules. Report interpretation and validated
pixel-based inference remain future work. The legacy `analyze_chest_xray` helper
is retained only for demonstration/tests; it is not on the live graph path.

The imaging page displays decision, status, requested study, reference, report,
and any override/handoff. The frontend no longer fabricates a scan path or
radiology impression when findings are empty. Skipped imaging is not displayed
as a normal scan. References are metadata: this phase does not upload, fetch,
or interpret image files. Optional reports should be supplied with intake or
the imaging decision; adding reports after a completed assessment requires a new
session. Old `cxr_path` text hints no longer imply clinical indication.

Verification covers no-imaging/optional continuation, existing reports, required
report blocking, unknown/unavailable handoff, explicit overrides, validation,
clinician ownership, persistence, and urgency precedence. The Phase 4 research
manuscript remains a historical snapshot; it was not rewritten for Phase 5.
