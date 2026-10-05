# Imaging assessment questions (Phase 12A)

Required imaging now records the clinician's assessment question alongside the
reason, modality and body region. An older intake without a question pauses for
that question before requesting a report. Marking the question unavailable ends
in clinician assessment rather than inventing an indication.

The question is clinician-authored; its indication is not independently verified.
A supplied report is retained verbatim and marked available for review. Receiving
a report does not establish that it answers the question. There is no pixel
inference, automatic interpretation or model-proposed imaging in this phase.

Required decisions are bound to a fingerprint of demographics, source notes,
observations, current calculator results (excluding calculation timestamps),
pathway decisions and urgency context. When those inputs change, the imaging node
clears the active report and requests a fresh decision. The clinician must supply
or reconfirm the study information. A replacement decision clears the prior
response so an old report or override cannot silently satisfy the new request.
Historical audit events remain available.

This freshness rule applies to required imaging. Optional and no-imaging decisions
retain their existing behavior. Legacy checkpoints without a fingerprint acquire
one when a required decision with a question is processed; prior freshness cannot
be established retroactively. Existing urgency checks and clinician ownership
requirements remain in effect. State uses existing JSON persistence, without a
database migration.

Verification includes question validation, legacy intake, unavailable-question
handoff, report status, unchanged and changed inputs, and API reevaluation with
report invalidation. The selected regression suite passed 385 tests, the strict
synthetic workflow evaluation passed 49/49 cases, and the frontend build passed.
These are software checks, not clinical validation or a browser usability study.

Phase 12B will address model-proposed imaging after assessment with explicit
clinician confirmation. The present graph still processes imaging before
diagnostic generation. Model generation remains disabled by default.
