# Phase 11 — bounded diagnostic clarification

The diagnostic node converts validated candidate `missing_information` identifiers
into optional clarification requests. The supported set is the seven existing
VitalSigns fields, with fixed unit labels. No model-written question, treatment,
new laboratory field or investigation order is accepted. Each field description
identifies the candidate(s) for which the model selected it; clinical relevance is
not independently established.

Questions are generated only after a valid candidate proposal. Model abstention
without candidates does not currently generate questions. The provider remains
disabled by default until deployment/model selection. Tests use synthetic providers;
no real model question-quality evaluation was performed.

Each request contains a mandatory workflow choice: provide values or proceed to
clinician review. Values themselves are optional for continuing the assessment.
When providing values, each requested field needs a valid number, explicit unknown,
or explicit unavailable answer. Unknown and unavailable are retained separately in
resolved requests and diagnostic followup context; neither becomes a measurement,
negative answer or normal finding. The clinician may instead proceed directly to
review, ending further diagnostic questions for that session. This does not skip
urgency review or authorize diagnosis/treatment.

Known observations and previously answered fields are excluded. Duplicate selections
are consolidated. A pending diagnostic request is reused by existing graph routing
rather than generating another. The planner limits requests to three fields per
round and two rounds per session. The count persists through triage and reevaluation;
reaching the limit leads to clinician review with remaining limitations, not an
implicit completion of clinical assessment. More fields may remain missing.

Responses require the authenticated session owner. Unexpected control fields and
out-of-range/nonfinite/non-numeric measurements are rejected. Diagnostic controls
cannot be submitted through another agent's request. New observations use the
existing validated response-to-state mechanism, invalidate derived results and
return through urgency and triage before diagnosis. Unknown/unavailable answers
and the continuation choice are included in diagnostic input fingerprints. New
fingerprint inputs mean older review checkpoints may require reevaluation.

Prompt version is differential-v2. The model receives previous followup answers
and instructions to select missing inputs only when clarification matters. These
prompt instructions are backed by server-side deduplication and limits. Every
request records field purposes, request ID and round in an audit event. Candidates
are marked provisional in the limitations while clarification is pending.

The modal distinguishes unknown/unavailable and lets the clinician continue without
entering measurements. In this mode it discards unsent numeric form entries; the
API rejects mixed bypass-plus-measurement payloads. No database migration is needed.

Verification: 374 selected regression tests passed (one existing Starlette warning),
including value reuse, deduplication, malformed values, unknown/unavailable handling,
owner enforcement, continuation, two full API clarification rounds and an urgent
observation that interrupts resumption before diagnosis. Frontend build passed.
Browser interaction, clinical relevance and real model behavior were not tested.

Next Phase 12: connect clinician-confirmed imaging decisions to explicit assessment
questions and evidence, retaining imaging scope and urgent-review boundaries.
