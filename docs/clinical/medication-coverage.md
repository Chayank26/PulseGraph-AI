# Medication coverage — Phase 13A

The safety node runs limited legacy local text-match alerts. Comprehensive drug
interaction checking is **not configured**. No alert must not be interpreted as
medication clearance. Existing local rules are retained, not clinically validated
by this phase. Dose, route, timing, ingredient normalization, renal and hepatic
dosing remain unassessed.

The retired RxNav interaction request and the associated first-word drug-name
lookup have been removed. Medication screening makes no external network calls.
NLM reports that its drug/drug interaction features ended January 2, 2024:
https://lhncbc-portal.lhcaws-prod-pub.nlm.nih.gov/RxNav/information/FAQs.html
(accessed October 5, 2026). RxNorm identifiers are not an interaction service.

Results expose `presentation.safety_review`, including local-rule version,
provider availability, medication/allergy recording status and limitations. Empty
lists mean not recorded, not a reconciled negative history. Whitespace-only entries
are ignored by local matching. Coverage is included in audit metadata and removed
when diagnostic results are invalidated. As derived output it is excluded from
diagnostic input fingerprints and model prompts. Existing JSON storage is reused.

The safety page displays coverage independently from alert count. It no longer
infers normal renal function, dose adjustment requirements, no known allergies or
a passed interaction audit from absent fields or keyword-only history. No browser
usability study was performed.

Verification: 403 selected software tests passed, plus the frontend production
build. Tests cover no-network execution, blank-entry handling, limited coverage
with and without alerts, persistence and invalidation. One existing Starlette
TestClient deprecation warning remains.

## Next: Phase 13B

Specify a replacement provider contract with versioned source provenance,
normalization ambiguity, partial coverage and explicit failure states. Selecting
and activating a real interaction dataset requires checking its access and license
terms and clinical scope. Add reconciled history states and evaluate the retained
local rules separately. No replacement provider, comprehensive screening, or
clinical validation is claimed in Phase 13A.

## Phase 13B — implemented contract and session reconciliation

The safety node now requests reconciliation when medication/allergy entries exist
or a legacy missing-medication marker requests history acquisition. Entirely empty
histories without that marker retain NOT_RECORDED status; they are not silently
converted to confirmed negatives. The session owner chooses recorded,
none_confirmed, unknown or unavailable independently for medications and allergies.
Recorded requires comma-separated entries; the other choices reject supplied list
text. Confirmed none clears the session list. Unknown/unavailable preserve earlier
entries as unverified context and explicitly label incomplete history.

Reconciliation binds to the exact medication/allergy lists. Changed lists request
reconciliation again. Resolved legacy markers no longer repeatedly request the same
history. The choices update session demographics/checkpoints, not the longitudinal
patient-directory record. Changes invalidate derived outputs and re-enter urgency
and triage before review. History states participate in diagnostic input fingerprints
and structured model context. Existing JSON persistence is reused without migration.

`src/tools/medication_provider.py` defines a strict, provider-neutral result contract:
provider name, source version, declared scope, normalization for every input, and
pair-level assessments with source references. Normalization distinguishes resolved,
ambiguous and unmatched names. Unknown indices, duplicate pairs, missing provenance
or assessed pairs using ambiguous ingredients reject the output. Missing/skipped
pairs produce PARTIAL coverage. Alerts require provider-supplied severity. Transport
or validation exceptions become FAILED without exposing raw exception text.

No adapter is configured in production. The default result remains NOT_CONFIGURED;
there is no network activity or fallback presented as complete coverage. A future
adapter must set transport timeouts, bound response sizes, verify source provenance
and license access, and undergo independent clinical testing. The contract validates
structure, not provider truthfulness or clinical completeness. Even
ASSESSED_WITHIN_PROVIDER_SCOPE does not certify medication safety. Allergy checking,
dosing and organ-function coverage remain subject to Phase 13A limitations.

Validation: the 418-test regression run passed, followed by 22 medication-focused
tests after adding explicit provider-severity and owner-authorization checks. The
frontend production build and 49/49 strict synthetic workflow cases also passed.
These use synthetic providers, not a live medication service or browser study.

The bounded Phase 13 engineering work is complete. Deployment still requires a
licensed, clinically reviewed provider and medication-rule review. Phase 14 is the
next roadmap item: a clinically specified non-cardiopulmonary pathway.
