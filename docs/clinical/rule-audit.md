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
