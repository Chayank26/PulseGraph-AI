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

## Phase 6: reproducible evaluation and expansion gate

Added an offline synthetic replay corpus and runner that execute the real graph,
including urgency and acquisition resumption, with isolated memory checkpoints.
The 49 scenarios span all nine presentation groups, three calculator pathways,
contextual assertions, conflicts, targeted questions, incomplete/unsupported
cases, urgency boundaries and acknowledgement, and optional/required imaging.
Expected outputs are explicit and the generated report retains mismatches,
source/corpus hashes, dependency versions, and rule configuration.

Initial result: 47 expectations satisfied and two documented language-coverage
gaps. The extractor does not recognize “pain in my chest,” and partial symptom
recognition can miss an unsupported concurrent complaint. These remain visible
known gaps, not successful clinical cases. Unexpected failures, runtime errors,
and unexpectedly fixed gaps fail the regression gate. A strict mode also fails
while any known gap remains. No new clinical pathway was added; expansion remains
blocked pending independent review and an annotated corpus.

See `docs/evaluation/README.md` for commands, scope, limitations, and entry
criteria for a new pathway. `docs/evaluation/triage-report.json` and `.md` record
the baseline. No database migration or frontend change is required. The research
paper remains the earlier Phase 4 snapshot, not a claim of these later results.

### Extraction gap follow-up

Rules-v2 adds bounded chest/abdominal/back pain paraphrases while preserving
assertion context and exact source spans. Unparsed narrative fragments now retain
source offsets and trigger clinician handoff even alongside a completed supported
calculator. This closes both original Phase 6 gap cases without relabeling their
expected outcomes. The corpus now has 49 passing cases and no known-gap markers.
The conservative residual-text check can also flag benign unfamiliar wording;
comprehensive language understanding and independent clinical validation remain
outside the demonstrated scope. No migration is needed: fragment fields default
to empty for older persisted presentations.

## Phase 7A: structured diagnostic inputs (completed)

Split Phase 7 into two reviewable increments. Phase 7A introduces a typed
DiagnosticContext carrying the validated presentation, exact source spans,
demographics/history/medications/allergies, available vitals and missing vital
fields, calculator results, applicability decisions, imaging plan/report, and
coverage limitations. The diagnostic audit records the context used for the run.
When no saved presentation exists, bounded extraction supplies a clearly marked
legacy fallback. A saved triage presentation remains authoritative.

The existing chest-pain and breathlessness candidate branches now require current
positive assertions. Absent, historical, other-person, uncertain, and conflicting
findings do not activate them. History-only and legacy simulated-imaging branches
were removed. Reports are retained without automatic interpretation; absence of
imaging is not normal imaging. Candidate evidence quotes only actual positive
source mentions. Unsupported probability labels, diagnosis codes and fixed
workup recommendations were removed from these demonstration candidates pending
clinical audit. These remain unvalidated candidate rules, not a diagnostic model.

Differentials now replace the previous graph result, including an empty result,
instead of accumulating across reevaluations. This does not yet invalidate stored
outputs immediately when upstream inputs change. Focused verification: 233 tests
passed, with one existing Starlette TestClient deprecation warning. No migration
or model/network service is introduced.

### Phase 7B: result freshness and frontend integration (next)

- Track the input revision used for diagnostic outputs and propagate invalidation
  through persisted results, downstream evidence, and clinician approval.
- Ensure changed inputs are re-extracted/reassessed before diagnostic reruns;
  Phase 7A deliberately trusts the supplied triage snapshot.
- Repair the existing frontend/backend differential schema mismatch (frontend
  expects disease_name and percentage likelihood; backend supplies condition_name
  and a textual likelihood). Display “Not estimated” without invented percentages.
- Expose context limitations and source evidence in diagnostic/review views.
- Verify API persistence, rerun/resume behavior and review freshness end to end.

### Subsequent roadmap

8. Inventory, source-check and clinically review deterministic rule semantics.
9. Implement traceable evidence retrieval with explicit insufficient support.
10. Add a bounded, schema-validated, evidence-grounded differential agent.
11. Add targeted follow-up questions with missing/unavailable handling and limits.
12. Connect clinician-confirmed imaging decisions to assessment questions.
13. Replace obsolete medication services and make coverage/failure explicit.
14. Add one clinically specified non-cardiopulmonary pathway.
15. Improve the consolidated clinician review workspace and versioned approval.
16. Independent clinical annotation, workflow evaluation and recovery testing.

Each increment includes regression checks and a stop for review with a short
suggested commit message. Independent clinical review and data/provider decisions
remain prerequisites where relevant; passing software tests does not establish
clinical validity. The manuscript remains its historical implementation snapshot.

## Phase 7B: result freshness and frontend integration (completed)

Diagnostic runs now record a stable fingerprint of session clinical inputs,
structured presentation and score content (excluding generated timestamps and
review metadata). The presentation stores current diagnostic review metadata and
limitations, using the existing JSON persistence field without a migration.
Approval requires a matching fingerprint at the human-review checkpoint; older
checkpoints without one require reevaluation.

Reevaluation clears diagnostic, evidence, safety and symbolic outputs and approval
before graph execution, and persists the clearing before continuing. Feedback is
retained as narrative for bounded extraction and passes through urgency and
triage, so a newly unsupported complaint can stop with a handoff. Contradictory
feedback requires clarification rather than silently replacing prior assertions.
Answers received after diagnosis also clear derived results and restart assessment.
Evidence, safety and symbolic output channels replace their previous lists rather
than accumulate obsolete entries. Reevaluation beyond the existing iteration cap
is rejected before altering results.

Frontend diagnostic, dashboard, review and export consumers now use the backend
condition_name/rationale/textual-likelihood fields. Removed the diagnostic
percentage meter and probability claims; source quotations and limitations are
visible. Approval is disabled for non-current or non-review states. The client
clears old derived results while reevaluation is pending and refreshes on failure.
Demo fixtures were updated to the same shape.

Validation: 239 focused regression tests passed; production frontend build passed.
New API tests cover persisted clearing on handoff, evidence replacement, successful
approval after reassessment, rejection of mismatched fingerprints, and the
iteration cap preserving current results. One existing Starlette deprecation
warning remains. Browser interaction testing was not performed.

Scope: fingerprints bind session snapshots, not subsequent edits to the separate
patient directory. This is not an atomic cross-store transaction or a concurrent
request locking mechanism; infrastructure recovery/concurrency testing remains
Phase 16. Narrative feedback remains subject to bounded extraction and may cause
conservative handoff. Diagnostic candidates and downstream clinical rules remain
unvalidated demonstrations. Phase 8 is next: clinical-rule inventory and audit.

## Phase 8A: clinical-rule inventory and symbolic restrictions (completed)

Phase 8 is split into 8A (inventory and removal of unsupported treatment overrides)
and 8B (calculator semantics, input contracts and urgency boundaries). The full
inventory and source-check status are in `docs/clinical/rule-audit.md`.

Four legacy symbolic rules are disabled: blanket beta-blocker withholding,
procedure escalation from simulated pneumothorax findings, contrast contraindication
from history keywords, and the mislabeled qSOFA/septic-shock treatment bundle.
No replacement treatment logic is introduced. Runtime metadata and audit events
explicitly report unavailable checks; symbolic and review views expose the
limitation. The limited urgency screen remains separate. Historical saved rule
outputs are not rewritten. Generated symbolic-review metadata is excluded from
patient-input fingerprints so review approval remains consistent.

Validation: focused regression suite (243 tests) passed; an additional API test
checks availability persistence and approval compatibility. Frontend production
build passed. Clinical approval is not claimed, and browser interaction was not
tested. Active calculator interpretation strings and medication-module rules still
require the explicitly documented follow-up audit; Phase 8 as a whole is unfinished.

Next: Phase 8B — verify calculator source definitions, repair input gaps, remove
unsupported probabilities/disposition text, attach provenance and test boundaries;
reconcile medication-module vital alerts with the existing urgency screen.

## Phase 8B1: calculator validation and output corrections (completed)

Phase 8B is split to keep arithmetic/output changes separate from clinical input
contract changes that affect questionnaires and resumed sessions. Removed fixed
probabilities and disposition/treatment instructions from HEART/CURB-65 output;
Wells now uses explicitly named NICE two-level classification. Added source,
version, pending-review metadata and complete Wells input provenance. Calculator
functions reject invalid inputs instead of clamping categories or accepting
truthy nonbooleans. HEART and CURB-65 disclose unresolved input coverage in details.

284 selected tests passed (one existing Starlette warning); no frontend change.
See `docs/clinical/rule-audit.md` for source verification and limitations.

Next 8B2: HEART atherosclerotic-history/risk-component collection and CURB-65 unit
contract, including missing/unavailable answers, followed by urgency boundaries
and removal/reconciliation of duplicate vital-treatment messages. Phase 8 remains
in progress; no clinical approval has been obtained.

## Phase 8B2: clinical input contracts and urgency boundaries (completed)

HEART now explicitly requests established atherosclerotic disease, uses two risk
points when present, and hands off if that input is unavailable. Old count-only
intake is not silently treated as negative. CURB-65 converts its explicitly labeled
BUN mg/dL input to mmol/L with the published 0.357 factor before comparing >7;
conversion provenance is saved. Calculator version advances to calculator-audit-v2.
Fixtures now explicitly provide the added input where intended. No schema migration.

Removed medication-module duplicate vital flags/treatment wording in favor of the
existing scoped urgency screen. Added fractional boundaries, scope tests and API
request/resumption/persistence coverage. 310 selected tests passed; regenerated
strict evaluation reports show 49/49 cases passing, expansion_ready remains false.
Clinical review and assay/category sign-off remain pending; see the rule audit.

Next: Phase 9 — traceable evidence retrieval, with source provenance and explicit
insufficient-support outcomes. The clinical-review requirement is not satisfied by
the completed software tests.

## Phase 9A: traceable local passage retrieval (completed)

Replaced fixed differential-to-citation branches and invented relevance scores
with a versioned local collection and deterministic topic-overlap retrieval.
Two short official-source excerpts seed the collection. Per-candidate outcomes,
source versions, timestamps and content hashes persist with results. Missing,
invalid, unmatched and out-of-review-date sources produce explicit limitations;
retrieved passages are related context only, never diagnostic confirmation.
Evidence UI shows provenance and actual status, with correct source links and
no fabricated percentage. Generated metadata is excluded from input fingerprints;
reevaluation invalidates evidence. No database migration or live network service.

316 selected tests and frontend build passed. Clinical retrieval quality and
browser interactions remain untested. See `docs/clinical/evidence-retrieval.md`.
Phase 9 is split: next 9B adds controlled source updates and claim-support review
contracts/evaluation. Comprehensive evidence grounding is not yet implemented.

## Phase 9B1: source-update reports and claim-review contracts (completed)

Added read-only `scripts.review_evidence` with full before/after record diffs,
content hashes, version/date/topic checks and nonzero failure exits. Added an
offline four-verdict claim-review schema bound to exact claim/corpus/passage and
review dates. Recorded reviewer names are not authenticated and cannot upgrade
runtime evidence support. No new medical content or live network access introduced.

72 focused tests passed across source review, retrieval, API freshness and synthetic
triage evaluation. No frontend change. Source expansion and independent clinical
support-quality evaluation remain incomplete. Next Phase 9B2 adds authenticated
review integration and ingestion/evaluation work; live matches remain context only.

## Phase 9B2: authenticated evidence review and retrieval evaluation (completed)

Added session-owner-only evidence judgment endpoints and a frontend review form.
Identity/time come from the server; judgments bind the actual candidate, passage,
corpus and diagnostic inputs. Stale or unavailable bindings are rejected. Stored
revisions are rechecked on read, and reevaluation clears current judgments while
retaining audit history. No automatic upgrade of evidence support or session
approval. Existing JSON storage is reused; no migration.

Added a ten-case developer-authored retrieval benchmark and hash-bearing report.
Synonym/negation limitations are explicitly documented, not presented as clinical
success. 330 focused tests passed and frontend build passed; browser interaction,
concurrency and independent clinical quality were not evaluated.

Phase 9's bounded engineering implementation is complete. Source expansion,
independent clinical annotation and automated ingestion are not implemented; the
manual source-update review process and two-source collection remain in place.
Next: Phase 10, bounded differential-agent implementation. Clinical effectiveness
and automated claim entailment remain unestablished.

## Phase 10: bounded differential agent (implemented; activation pending)

Replaced production keyword diagnosis with a provider-independent, schema-validated
proposal contract. Added local Ollama adapter, bounded requests/responses, explicit
abstention/failure, grounded finding/document references, model/prompt/corpus audit
metadata and clinician-visible source/missing/conflicting information. Unknown
references and wrong assertion statuses reject the output; no probabilities or
automatic workup are generated. Structural grounding is not clinical entailment.

Generation is disabled by default until a deployment/model is selected. No live
model or external patient-data transfer was used. Test-only synthetic providers
keep workflow regressions deterministic; they are not a production fallback.
See `docs/clinical/differential-generation.md` for configuration and limitations.

Next Phase 11: validated targeted follow-up questions and bounded clarification.
Actual model activation and independent clinical evaluation remain required before
claiming model-backed diagnostic quality or real-world benefit.

Phase 10 verification: 357 focused tests passed; 49/49 strict workflow cases passed;
frontend production build passed. The local adapter was tested with a stub transport,
not a running model. Actual activation remains pending the deployment selection.

## Phase 11: bounded targeted follow-up questions (completed)

Valid diagnostic proposals can request optional clarification of existing missing
observation fields. Questions name their candidate purpose, reuse known/answered
values, preserve unknown versus unavailable, and allow clinician-directed review.
Limits are three fields per round and two rounds per session. New measurements
invalidate derived outputs and pass through urgency/triage again. Ownership and
response validation apply at the API; followup state participates in freshness
fingerprints. Prompt version is differential-v2. No database migration.

Scope is the existing seven observation fields, not arbitrary generated questions
or test orders. Abstention-only model outputs do not request clarification. Live
model activation remains pending. See `docs/clinical/diagnostic-questions.md`.

374 selected tests passed and frontend build passed. Next: Phase 12, imaging
recommendations connected to assessment questions with clinician confirmation.

## Phase 12A: clinician-authored imaging questions and freshness (completed)

Phase 12 is split because imaging currently precedes diagnostic generation.
Required imaging now records an explicit assessment question, requesting it from
legacy intake when absent. An unavailable question leads to clinician assessment.
A supplied report is available for review, not automatically an answered question
or a verified indication. The UI exposes these distinctions.

Required plans bind to the current intake, observations, calculator results and
routing context. Changed inputs clear the active report and require a fresh
imaging decision; replacing a decision clears old responses and overrides.
Existing urgency and ownership checks remain. No database migration.

385 selected regression tests passed, 49/49 strict synthetic workflow cases passed,
and frontend production build passed. See `docs/clinical/imaging-assessment.md`
for scope and legacy-checkpoint limitations.

Next: Phase 12B, model-proposed imaging after assessment with clinician confirmation.
That capability is not implemented in 12A; model generation remains disabled by
default. Optional/no-imaging freshness and clinical indication validation are not
established by this phase.

## Phase 12B: model-proposed imaging with clinician confirmation (completed)

The differential-v3 schema permits one candidate-linked imaging suggestion with
an assessment question and structurally validated evidence references. Suggestions
open an explicit owner-only clinician review after diagnostic clarification.
Reject/optional/required/uncertain decisions require a written reason; only a
clinician-required decision requests a report. Responses clear stale derived
outputs, pass through urgency/triage, and preserve the existing report override and
handoff behavior. One suggestion review per session prevents repeat model loops.

The intake imaging step remains; this adds a post-diagnostic review checkpoint.
The existing generic request UI is reused, without preselected answers or a schema
migration. Model generation remains disabled by default. See
`docs/clinical/imaging-assessment.md` for limitations and activation boundaries.

398 selected regression tests passed and 49/49 strict synthetic workflow cases
passed. Tests use synthetic providers, not live-model or clinical evaluation.

## Phase 13A: retire obsolete medication service and expose coverage (completed)

Removed the discontinued RxNav interaction call and its first-word identifier
lookup from medication screening. Limited local alerts remain, with explicit
provider-not-configured status, rule version and coverage limitations stored in
results and audit metadata. Empty histories are not treated as confirmed negatives.
Blank entries no longer create substring allergy matches. Derived coverage is
excluded from diagnostic fingerprints/model prompts and cleared on invalidation.

The safety UI now reports coverage independently of alerts and removes unsupported
renal clearance, dose adjustment, NKDA and drug-audit-pass claims. Existing JSON
storage is reused. See `docs/clinical/medication-coverage.md`.

403 selected tests and the frontend production build passed. Next Phase 13B:
replacement-provider contract, normalization/coverage failure handling and explicit
medication-history reconciliation. Real provider activation and clinical review
remain outstanding; Phase 13 is not complete.

## Phase 13B: provider contract and session history reconciliation (completed)

Added a strict provider-neutral interaction result contract with source version,
normalization ambiguity, pair-level provenance, partial coverage and explicit
failure states. No production adapter is configured; synthetic providers exercise
the contract. Provider-reported alert severity is required rather than invented.

Medication/allergy entries or a legacy missing-history marker now trigger owner-only
reconciliation. Recorded/confirmed-none/unknown/unavailable remain distinct, unknown
preserves earlier unverified entries, and changed lists require renewed review.
Responses update session state, invalidate derived results and pass through urgency
and triage. Entirely empty histories remain NOT_RECORDED unless acquisition was
requested. The UI shows history and provider coverage states. No database migration.

418 regression tests passed; 22 medication-focused tests passed after final severity
and ownership additions. Frontend build and 49/49 synthetic workflow cases passed.
See `docs/clinical/medication-coverage.md` for scope and deployment limitations.

Next Phase 14: a clinically specified non-cardiopulmonary pathway. Phase 13's bounded
engineering work is complete; live provider selection/activation and independent
clinical review remain outstanding and are not implied by test success.

## Phase 14: bounded adult low-back assessment (implemented; clinical review pending)

Added a non-cardiopulmonary pathway for clinician-confirmed adult low-back pain,
informed by NICE NG59 assessment principles. General back-pain extraction nominates
it; clinician confirmation establishes location and non-pregnant adult scope.
Recorded pediatric/pregnancy exclusions are enforced before entry. The owner records
scope and suspicion of a specific/serious cause. Unknown, unavailable, outside-scope
or concerning answers hand off before imaging/diagnosis; completed assessment records
clinician judgment without a score, diagnosis, low-risk claim or treatment advice.

The assessment binds to current inputs and is renewed after changes. Unsupported
co-complaints remain visible. The frontend displays answers, limitations and source.
Existing persistence is reused. No new model knowledge corpus or automatic imaging
recommendation was added. See `docs/clinical/low-back-assessment.md` for the clinical
specification, implementation boundaries and independent-review requirement.

436 selected tests and frontend build passed. The synthetic evaluation collection
now contains 51 cases. Next Phase 15: consolidated clinician review workspace and
versioned approval. Clinical review of this new pathway remains outstanding.

## Phase 15: consolidated review and versioned approval (completed)

The review workspace now displays one versioned checkpoint package with all clinical
outputs and coverage limitations. Approval submits that displayed version, rejects
missing/stale versions, and records the authenticated owner, server time and version
in state/results/audit. Review package access, reassessment and rejection also require
the session owner. UI acknowledgement is explicit and failed actions require reload.
Export remains a stub and is no longer described as actual EHR delivery in review.

440 selected tests and frontend build passed. No migration. See
`docs/clinical/versioned-review.md` for the changed API contract and remaining
limitations. Version checking is optimistic, not atomic across database/checkpoint
writes; concurrent approval safety and failure recovery remain Phase 16 work.

Next Phase 16: independent clinical annotation, workflow/human-factors evaluation
and recovery/concurrency testing. Clinical validation and real-provider activation
remain outstanding across earlier phases.

## Phase 16A: offline recovery-boundary gate (completed)

Added a reproducible JUnit-backed recovery report with test hashes, backend identity
and explicit untested-concurrency/clinical flags. Loss of checkpoint state now returns
a review conflict instead of an empty package; pending answers remain unconsumed.
Resolved request retries return conflicts without resuming. Explicit PostgreSQL
requests cannot silently fall back to memory; implicit development fallback remains.

Nine recovery/versioned-approval checks passed, 445 selected regression tests passed,
and 51/51 synthetic workflow cases passed. No frontend changes. Reconstruction tests
share an in-process saver and must not be reported as PostgreSQL crash recovery.
See `docs/evaluation/recovery-protocol.md` and `recovery-report.json`.

Next Phase 16B: disposable PostgreSQL failure injection, coordinated concurrent
mutations and transaction/serialization fixes, plus independent clinical evaluation
preparation. Automatic recovery, atomic approval, exactly-once audit persistence and
independent clinical validation remain unestablished. Phase 16 is not complete.

## Phase 16B1: per-session serialization and PostgreSQL lock probe (completed)

Added PostgreSQL advisory locking around workflow mutations, evidence submission and
versioned review reads. A dedicated connection holds the lock across repository
commits; competing operations conflict instead of interleaving, while separate
sessions can progress. SQLite supports process-local development/test locks only.
Approval now validates its version inside the shared operation lock. Reassessment
and rejection return HTTP 409 for workflow conflicts.

447 selected regression tests passed, along with all nine offline recovery gate
checks. A real PostgreSQL 16 disposable container passed the independent-process
probe: conflict survives application commits, different sessions remain independent,
and worker termination releases the lock. The temporary container was stopped and
removed. See `docs/evaluation/postgres-lock-report.json` and
`docs/evaluation/session-serialization.md`. No frontend changes.

Next Phase 16B2: full PostgreSQL workflow restart/partial-commit injection and
reconciliation, lock-connection-loss fencing, service-level process races and
idempotent audit persistence. Advisory locking is not an atomic application/checkpoint
transaction; automatic recovery and clinical validation remain unestablished.

## Phase 16B2: stable-checkpoint projection recovery (completed)

Request resolution now persists the checkpoint before database response status.
Synchronization preserves actual resolved/pending states and timestamps and deduplicates
checkpoint audit events under the session lock. Added owner-only POST /recover to
reconcile database projections at stable graph boundaries without replaying clinical
actions. Missing, mid-transition and interrupted-approval checkpoints are refused.
Historical audit duplicates remain; no database migration or frontend change.

A disposable PostgreSQL 16 / PostgresSaver experiment passed three fresh-process stages
with injected result-write failures, reconstruction, request resolution and repeat
reconciliation. The container was removed. 451 selected tests passed, followed by six
focused recovery tests after final refusal checks. See
`docs/evaluation/projection-recovery.md` and `postgres-recovery-report.json`.

Next Phase 16B3: mid-transition/approval recovery protocol, lock-connection-loss fencing
and full service-process races. Cross-store atomicity, abrupt-crash recovery and
independent clinical validation remain outstanding; Phase 16 is not complete.

## Phase 16B3A: interrupted approval recovery (completed)

Owner recovery now returns attributable/current approval interruptions at human_review
or before the export stub to a new review checkpoint. Prior intent remains in the
audit trail; active approval is cleared and a fresh review version is required.
Completed approvals are preserved. Projection retries do not reset the review twice.
The workspace displays an explicit return-to-review action for interrupted approval.
Unattributed/stale approval and other mid-transition checkpoints remain refused.

457 selected tests, 19 recovery gate checks and frontend build passed. A disposable
PostgreSQL/PostgresSaver probe passed three fresh-process stages: injected approval
interruption, recovery/new approval, and terminal verification. The container was
stopped and removed. See `docs/evaluation/approval-recovery.md` and the committed
`postgres-approval-recovery-report.json`. No schema migration or live model use.

Next Phase 16B3B: lock-connection-loss fencing, other mid-transition protocols and
full service-process races. Cross-store atomicity and clinical validation remain
outstanding. Export remains a stub; real delivery would require a separate receipt
and idempotency design before using this recovery policy.

## Phase 16B3B: detected lock-loss fail-stop guards (completed)

Serialized operations now verify PostgreSQL backend identity and advisory ownership
before ORM flush/commit, synchronous checkpoint mutations and operation completion.
Loss is sticky: the operation refuses subsequent writes rather than reacquiring and
continuing. Uncommitted application work is rolled back, late checkpoint writes use
closed guards, and listeners/saver adapters are removed after the operation.

464 selected tests and 28 recovery checks passed. A disposable PostgreSQL backend-
termination probe passed checkpoint-write refusal, application rollback and new-worker
lock acquisition. Both real PostgresSaver fresh-process recovery probes also passed
with the adapter. The temporary container was stopped and removed. No frontend change
or schema migration. See `docs/evaluation/lock-loss.md` and its JSON probe report.

This is detection/fail-stop behavior, not storage-level fencing: loss between a check
and the next write is still possible. Next Phase 16B3C must design and enforce atomic
ownership/fencing at both persistence stores and test that precise race. Other
mid-transition protocols and independent clinical evaluation remain outstanding.
