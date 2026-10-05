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
