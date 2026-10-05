# Clinical rule audit — Phase 8A

Technical inspection: October 5, 2026. No clinician approval is claimed.
Status vocabulary: **disabled**, **active prototype / review pending**, and
**legacy utility**. Source verification does not validate this implementation.

## Executable rule inventory

| Rule / location | Inputs and implemented scope | Audit status and next action |
|---|---|---|
| HEART, `src/tools/calculators.py` | History/ECG/troponin categories, age and risk-factor count; triage requires clinician applicability, excludes recorded under-18 and pregnancy | Active prototype / review pending. Remove fixed event probabilities and disposition/invasive-treatment instructions. Count-only risk factors do not explicitly represent established atherosclerotic disease; resolve input contract before calling the implementation complete. Clamping invalid category values should become validation. |
| CURB-65, same file | Confusion, BUN mg/dL, respiratory rate, both blood pressures, age; clinician-confirmed adult hospital pneumonia context | Active prototype / review pending. Audit BUN/urea unit conversion and threshold; current docstring confuses analytes. Separate numeric result from mortality percentages and treatment location. Boundary tests required in 8B. |
| Wells PE, same file | Seven boolean criteria; clinician-confirmed suspected PE | Active prototype / review pending. Current three-band output is not the NICE two-level pathway. Remove fixed probabilities; explicitly choose/version the interpretation. Preserve all seven input values in result provenance. |
| BMI, same file | Weight and height, adult categories; not selected by current triage router | Legacy utility. Finite/nonnegative input checks and intended-population documentation pending; no pediatric interpretation. |
| Urgency HR | ≤40 or ≥131 bpm | Active prototype / clinical review pending; selected extreme-observation bands only. |
| Urgency respiration | ≤8 or ≥25 breaths/min | Same; no aggregate NEWS2 score. |
| Urgency systolic BP | ≤90 or ≥220 mmHg | Same; not a diagnosis or disposition. |
| Urgency temperature | ≤35 °C | Same; does not assess all temperature abnormalities. |
| Urgency SpO2 | ≤91%, explicit standard-scale applicability | Same; individualized scale is not implemented. |
| Urgency confusion | Explicit new confusion | Same; unknown is not negative. |
| Urgency clinician concern | Explicit clinician concern independent of observation-screen scope | Active prototype / clinical review pending; prompts clinician acknowledgment. |
| Symbolic beta blocker rule | HR <50 plus substring medication match | **Disabled.** Missing medication-specific context; blanket hold instruction unsupported by implementation evidence. |
| Symbolic pneumothorax rule | Legacy imaging label plus confidence ≥0.85 | **Disabled.** No validated pixel inference or tension-physiology assessment; procedure instruction unsupported. |
| Symbolic contrast rule | Kidney/renal history substring plus CT/angiogram workup, gated by nonzero BP | **Disabled.** No demonstrated contrast exposure or renal-function assessment; hard contraindication not established. |
| Symbolic sepsis rule | SBP <90, RR ≥22, temperature >38 | **Disabled.** Incorrect qSOFA/septic-shock label and automatic treatment bundle. No replacement sepsis classifier introduced. |
| Diagnostic candidates | Current-positive chest pain / breathlessness | Active demonstration / review pending. No diagnostic probabilities, codes or automatic workup; not comprehensive diagnostic coverage. |
| Medication allergy matching | Substrings and penicillin/sulfa/aspirin cross-match lists | Active legacy component / unreviewed. Blanket contraindication wording and coverage need audit; not comprehensive allergy assessment. |
| Interaction lookup and fallback | RxNav legacy interaction URL, medication identifier lookups; local warfarin/NSAID rule | Active legacy component / unreviewed. Obsolete endpoint and silent failure semantics remain Phase 13 work. No-alert cannot establish safety. |
| Medication-module vitals | SpO2 <90, HR >130, truthiness-based checks | Active legacy component / unreviewed. Duplicates urgency with different scope and treatment language; consolidate or disable in 8B after source review. |
| Evidence node | Fixed references selected from candidate labels | Demonstration; not verified patient-specific evidence. Replacement planned in Phase 9. |

Urgency physiology scope is recorded age ≥16 and explicit non-pregnancy. Missing
observations and unsupported oxygen scales remain explicit. Its defaults retain
PENDING_CLINICAL_REVIEW; acknowledgement is not rule approval. Calculator routing
has a different age/pregnancy policy, which requires explicit clinical review.

## Source checks and provenance

- [Sepsis-3, JAMA (2016)](https://jamanetwork.com/journals/jama/fullarticle/2492881):
  verified qSOFA uses respiratory rate, mentation and systolic pressure in suspected
  infection. Fever is not one of those criteria. qSOFA is not the septic-shock
  definition. This directly supports retiring the mislabeled legacy rule.
- [NICE NG158](https://www.nice.org.uk/guidance/ng158/chapter/Recommendations):
  verified the two-level Wells PE split is >4 versus ≤4. The existing code instead
  has three strata; source choice and implementation must be explicitly reconciled.
- [RCP NEWS2 report (2017)](https://www.rcp.ac.uk/media/a4ibkkbf/news2-final-report_0_0.pdf):
  official report retrieved. PulseGraph is a selected-observation screen, not the
  complete NEWS2 scoring and escalation protocol. Full boundary audit remains 8B.
- [NICE NG250](https://www.nice.org.uk/guidance/ng250/chapter/Recommendations):
  current recommendations page returned HTTP 403 during this audit. Do not treat
  the retrieved draft document as the final specification. Reverify in 8B.
- [Original HEART study](https://doi.org/10.1007/BF03086144):
  carried forward from manuscript bibliography. PMC access hit a browser challenge;
  exact criteria and implementation comparison remain 8B work.

The first three symbolic rules are disabled because the code lacks sufficient
inputs/provenance for the instructions it issued. This is an engineering
restriction, not a claim that their clinical topics are unimportant or that all
such interventions are inappropriate.

## Runtime behavior and release boundary

The symbolic node now emits no treatment overrides, persists availability and
per-rule reasons under presentation.symbolic_review, and writes an unavailable
check audit event. The UI exposes those reasons. The existing graph step name is
retained for compatibility; it does not certify a completed safety assessment.
Old saved sessions may still contain historical overrides; new runs replace them.
Symbolic review metadata is excluded from the diagnostic input fingerprint since
it is generated downstream and is not patient input.

Reactivation requires a sourced intended-use specification, qualified clinical
review, typed inputs including unknown/unavailable semantics, and tests of
boundaries and exclusions. Do not reactivate rules by changing a status label.
No active symbolic evaluator exists in this revision.

## Phase 8B completion criteria

1. Resolve calculator input gaps and unit definitions against accessible primary sources.
2. Validate calculator inputs without silent clamping; test boundary values.
3. Remove unsupported risk probabilities and automatic disposition/treatment text.
4. Attach version/source/scope/review metadata to active calculator outputs.
5. Reconcile duplicate medication-module vital alerts with the limited urgency screen.
6. Test all urgency threshold boundaries and unsupported populations.

Phase 8A does not certify all active clinical content. Clinical sign-off, medication
knowledge replacement, and independent evaluation remain outstanding.

## Phase 8B1 update — calculator validation and output semantics

Completed October 5, 2026. This subsection supersedes the interpretation-text and
silent-clamping findings above; unresolved input-contract findings remain open.

- HEART and CURB-65 now emit score bands with clinician-review wording, without
  fixed outcome probabilities, discharge instructions or invasive-treatment advice.
- Wells retains the seven existing point weights and now explicitly uses the NICE
  two-level classification (>4 versus ≤4). Neither label confirms or excludes PE.
  All seven supplied inputs are retained in score details.
- These three calculators expose a rule version, source, pending-clinical-review
  status and a limitation in result details. This metadata is not clinical approval.
- Invalid categories, booleans-as-numbers, negative/nonfinite measurements and
  nonboolean criterion answers are rejected by calculator functions. HEART no
  longer silently clamps out-of-range categories. BMI gets numeric input checks.
- HEART's missing atherosclerotic-disease input and CURB-65's legacy >19 mg/dL BUN
  threshold are explicitly disclosed in result details. They are not corrected or
  certified by this increment. No new fallback or inferred answer was introduced.

Source checks: NICE NG158 table 2 was retrieved through search and supports the
implemented two-level Wells classification. The official HEART author flyer at
https://www.heartscore.nl/resources/flyer.pdf was retrieved and explicitly includes
atherosclerotic disease in the risk component. Its age/troponin boundary wording
requires reconciliation with the original study before finalizing the input
contract. Existing age calculations are retained, with boundary regression tests;
these tests document behavior rather than resolve the source ambiguity. CURB-65's
original-study DOI is provenance, not a claim of completed unit verification.

Validation: 284 selected tests passed, including calculator invalid-input and
boundary cases, workflow regression cases and API freshness tests. One existing
Starlette deprecation warning. No frontend changes or browser test in this increment.

Next 8B2: explicit HEART risk-component contract, exact CURB-65 units and conversion,
request/resumption updates, fixture migration, full urgency boundaries and duplicate
medication-module vital alerts. Existing numerical scores may still be limited by
those unresolved contracts; this is a prototype, not clinically approved scoring.

## Phase 8B2 update — clinical input contracts and urgency boundaries

HEART now requires an explicit `atherosclerotic_disease` boolean in both the
calculator and the triage request contract. A true answer assigns two risk-component
points regardless of count. A false answer uses the existing count mapping.
Missing answers are requested, not inferred from history keywords; unavailable
answers produce an incomplete-assessment handoff. Existing saved sessions with
count-only inputs must provide this additional answer on reassessment. No database
migration is needed. Synthetic fixtures explicitly record negative history where
that is the intended test case; missing-history behavior has its own regression.

CURB-65 retains the `bun_mg_dl` field, explicitly meaning blood urea nitrogen in
mg/dL. It converts using 0.357 to mmol/L and compares the unrounded value with >7.
It does not accept urea mg/dL or mmol/L in that field. The factor and converted value
are persisted in score details; calculator version is now calculator-audit-v2.
Values between the old >19 threshold and the converted threshold can change score.
The conversion factor is a published rounded convention, not an assertion of
unlimited laboratory precision. Previously saved scores are not rewritten.

Sources verified October 5, 2026:
- Author HEART chart: https://www.heartscore.nl/resources/flyer.pdf (atherosclerotic history).
- Original CURB-65 abstract: https://pubmed.ncbi.nlm.nih.gov/12728155/
  and publisher PDF search record: https://thorax.bmj.com/content/thoraxjnl/58/5/377.full.pdf
  (urea >7 mmol/L). Publisher HTML returned 403; the primary-study abstract and
  indexed PDF supply the criterion.
- Labcorp conversion table: https://www.labcorp.com/test-menu/resources/si-unit-conversion-table
  (BUN mg/dL to mmol/L factor 0.357).
- Current NICE NG250 recommendations were accessible through indexed search at
  https://www.nice.org.uk/guidance/NG250/chapter/recommendations.

Medication-module duplicate SpO2/heart-rate flags and automatic oxygen-treatment
wording were removed. Vital observations continue through the independent scoped
urgency node. This does not expand urgency coverage or validate medication safety.
Added fractional threshold-adjacency tests for every physiological urgency bound,
and age-16/pregnancy applicability tests. Existing missingness, acknowledgment,
clinician-concern and individualized-oxygen tests remain in the focused suite.

Validation: 310 selected tests passed; strict synthetic evaluation 49/49 passed.
Includes API acquisition/resumption/persistence, unavailable history, invalid
history type, BUN threshold conversion and urgency boundaries. One existing
Starlette warning. No frontend source changes or browser interaction tests.

Clinical approval remains pending. HEART age/troponin category definitions and
local assay interpretation still require qualified clinical sign-off (the source
flyer's boundary wording was noted above). No diagnostic validation, medication
knowledge completeness, or real-world effectiveness is claimed. Phase 8's
technical changes are complete; the independent review requirement remains open.
