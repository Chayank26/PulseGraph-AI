# Synthetic triage evaluation

Developer-authored synthetic graph replay; not clinical accuracy, independent validation, API authorization, or persistence testing.

Cases: **51**. Outcomes: `{"PASS": 51}`.

Passing regression checks does not authorize clinical deployment or new pathways.

| Category | Pass | Known gap | Failure/error/unexpected pass |
| --- | ---: | ---: | ---: |
| assertion context | 5 | 0 | 0 |
| conflicts | 3 | 0 | 0 |
| coverage boundaries | 6 | 0 | 0 |
| data acquisition | 4 | 0 | 0 |
| imaging decisions | 6 | 0 | 0 |
| language challenges | 2 | 0 | 0 |
| presentation groups | 11 | 0 | 0 |
| supported calculations | 3 | 0 | 0 |
| urgency precedence | 9 | 0 | 0 |
| urgency scope | 2 | 0 | 0 |

## Cases

| Case | Outcome | Gap or mismatch |
| --- | --- | --- |
| unsupported-abdominal_pain | PASS |  |
| unsupported-headache | PASS |  |
| unsupported-rash | PASS |  |
| unsupported-dysuria | PASS |  |
| back-pain-applicability | PASS |  |
| unsupported-fever | PASS |  |
| candidate-cardiovascular | PASS |  |
| candidate-respiratory | PASS |  |
| candidate-vascular | PASS |  |
| assertion-denied | PASS |  |
| assertion-historical | PASS |  |
| assertion-relative | PASS |  |
| assertion-uncertain | PASS |  |
| negation-boundary | PASS |  |
| conflict-pauses | PASS |  |
| conflict-absent | PASS |  |
| conflict-uncertain | PASS |  |
| heart-complete | PASS |  |
| curb-complete | PASS |  |
| wells-complete | PASS |  |
| multiple-concerns | PASS |  |
| applicability-not_applicable | PASS |  |
| applicability-unknown | PASS |  |
| excluded-child | PASS |  |
| excluded-pregnancy | PASS |  |
| missing-age | PASS |  |
| unavailable-age | PASS |  |
| heart-targeted-questions | PASS |  |
| unavailable-score | PASS |  |
| urgency-heart_rate_bpm-40 | PASS |  |
| urgency-heart_rate_bpm-131 | PASS |  |
| urgency-respiratory_rate-8 | PASS |  |
| urgency-respiratory_rate-25 | PASS |  |
| urgency-blood_pressure_sys-90 | PASS |  |
| urgency-blood_pressure_sys-220 | PASS |  |
| urgency-temperature_c-35 | PASS |  |
| urgency-spo2_percent-91 | PASS |  |
| urgent-ack-resumes | PASS |  |
| individualized-oxygen | PASS |  |
| unknown-pregnancy | PASS |  |
| imaging-no_imaging | PASS |  |
| imaging-optional | PASS |  |
| imaging-uncertain | PASS |  |
| required-report_provided | PASS |  |
| required-requires_clinician_assessment | PASS |  |
| required-overridden | PASS |  |
| unknown-complaint | PASS |  |
| gap-paraphrase | PASS |  |
| gap-partial-recognition | PASS |  |
| back-pain-handoff-suspected | PASS |  |
| back-pain-handoff-__unavailable__ | PASS |  |

## Expansion gate

- Independent clinician review and an annotated evaluation corpus are absent.
- Any known gaps listed below must be assessed before broadening coverage.
- Downstream diagnostic and evidence nodes remain bounded demonstration logic.

Machine-readable expected and observed values, source hashes, and rule configuration are in the companion JSON report.
