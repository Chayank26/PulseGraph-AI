# Adult low-back clinician assessment — Phase 14

This pathway records clinician assessment for a recognized current back-pain
presentation. It is not a calculator, diagnosis, exhaustive red-flag detector,
treatment protocol or clinically validated risk stratifier.

## Source and scope

NICE NG59, recommendation 1.1.1, calls for considering alternative diagnoses and
specific causes during assessment. Its assessment principles inform the clinician
prompt; the application does not implement the full guideline.
Source: https://www.nice.org.uk/guidance/ng59/chapter/recommendations
Checked October 5, 2026. Version: low-back-assessment-v1.

The prototype restricts eligibility to age 18 or older and clinician-confirmed
non-pregnancy and low-back location. This is narrower than the guideline's age
scope. Existing extraction recognizes back pain generally; the clinician must
confirm the location and eligibility. Recorded age below 18 or known pregnancy
prevents pathway entry. Missing age uses existing intake handling.

## Workflow

1. A current recognized back-pain symptom nominates the pathway. Negated or
   historical symptoms do not activate it. Applicability is explicitly confirmed.
2. The session owner records scope and whether a specific/serious cause is
   suspected after clinical history and examination. The prompt provides examples,
   not a complete neurological or emergency assessment.
3. Outside-scope, uncertain, unavailable or suspected-cause answers terminate in
   clinician-assessment handoff before downstream imaging and diagnosis. The UI
   does not select an emergency timeframe or claim treatment has occurred.
4. Confirmed scope and no clinician suspicion produce CLINICIAN_ASSESSED, without
   a numeric score or low-risk designation. Other unsupported complaints retain
   their handoff reasons. Existing imaging decisions remain separate.

The existing urgency node still runs first and after data-request resolution.
Patient demographics, narrative, observations, urgency context and pathway version
bind the recorded assessment to its inputs. Changes request renewed assessment.
Answers stay structured, are audited, and are not appended as symptom narrative.
Existing session JSON/checkpoint storage is reused without a migration.

## Boundaries and verification

The pathway cannot independently exclude serious disease. It relies on clinician
judgment and does not establish clinical competence, examination completeness,
referral completion or diagnostic safety. The source corpus for model generation
has not been expanded into a low-back diagnostic knowledge base. No treatment,
prescribing, imaging indication or automatic referral has been added. Independent
clinical review and evaluation remain necessary before clinical deployment.

Verification passed 436 selected software tests and the frontend production build.
The synthetic workflow collection now contains 51 cases, including low-back
applicability and suspected/unavailable-cause handoffs. Tests also cover scope
exclusions, unsupported co-complaints, malformed responses, session ownership,
persistence and reassessment. Tests are developer-authored fixtures, not a clinical
cohort or independent clinical validation.
