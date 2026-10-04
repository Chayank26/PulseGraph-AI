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
