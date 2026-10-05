# Phase 6: synthetic triage evaluation

This is a reproducible software evaluation of the Phase 1–5 workflow. It is not
an independent clinical benchmark, a clinical trial, or evidence of diagnostic
accuracy. No clinical pathways or urgency thresholds were added in this phase.

The checked-in corpus contains 49 developer-authored cases with explicit expected
outcomes. It covers all nine presentation groups, assertion context, conflicts,
calculator applicability, targeted questions, missing/unavailable inputs,
multiple complaints, scope exclusions, urgency precedence and acknowledgement,
and no-imaging/optional/required/uncertain imaging decisions.

## Run

From the repository root with the existing virtual environment:

```sh
PYTHONDONTWRITEBYTECODE=1 DEBUG=false CHECKPOINT_BACKEND=memory \
  venv/bin/python -m scripts.evaluate_triage
```

The runner writes `docs/evaluation/triage-report.json` and `triage-report.md`.
Use `--output /tmp/triage-report.json` for an ephemeral report. The JSON includes
expected and observed outcomes, exact mismatches, source and corpus SHA-256
hashes, dependency versions, and the urgency rule configuration used. A report
belongs to that source/corpus/configuration snapshot and should be regenerated
after relevant changes.

Default exit status is 1 for an unexpected failure, runtime error, or a known gap
that unexpectedly passes and needs reclassification. To also fail while any
known coverage gap remains:

```sh
PYTHONDONTWRITEBYTECODE=1 DEBUG=false CHECKPOINT_BACKEND=memory \
  venv/bin/python -m scripts.evaluate_triage --require-no-known-gaps
```

This stricter command now exits **0**: both previously documented cases meet
their expected behavior. The normal regression gate and readiness to expand clinical scope
are separate: the report always marks expansion unready pending independent
clinical review and an annotated evaluation corpus.

## How cases are executed

`tests/fixtures/evaluation/triage_cases.json` holds the input and expected behavior;
it is not generated from observed outputs. Each case creates a fresh real
LangGraph workflow with a MemorySaver checkpointer and synthetic clinician.
Explicit scripted responses use the same response validator and state update
functions as the service, then resume via the actual data-review/urgency edges.
The runner stops at unanswered requests, human review, or terminal handoff.
It bounds replay at 16 acquisition checkpoints and graph recursion at 60.

Dynamic request IDs, timestamps, and urgency fingerprints are excluded from
comparisons. `$urgency_ack` maps to the active urgency acknowledgement field.
Question traces include required field names, requesting agent, and pathway.
Every expectation explicitly listed in a case is compared exactly; an omitted
expectation is not assessed. An explicit null means that output must be absent.
The expected score values are software formula checks, not clinical risk claims.

No patient records, images, model providers, or external clinical services are
used. The input schema omits medication lists, preventing network-dependent
pharmacology calls in these cases. Evaluation tests also prohibit socket
connections. The runner does not test authentication, database persistence,
browser interactions, real image interpretation, or patient outcomes; existing
API regression tests remain the evidence for their narrower tested contracts.

## Previously observed gaps (now regression cases)

| Case | Fix |
| --- | --- |
| `gap-paraphrase` | Explicit chest-pain paraphrases are recognized with original source spans and assertion context. |
| `gap-partial-recognition` | Unparsed narrative fragments are preserved with source spans and trigger clinician handoff even when a supported calculator completes. |

Both cases now pass normally; their desired expectations were retained and only
`known_gap` labels were removed. Rules-v2 masks recognized concepts, bounded
attributes, and a small grammar vocabulary, then flags remaining narrative text.
This intentionally favors handoff over assuming complete coverage. Benign text
outside the small grammar vocabulary can also cause handoff. It is not unrestricted
language understanding, and these two fixes do not establish perfect extraction.
The evaluator still supports explicit known-gap cases and treats runtime errors
or unexpectedly passing known gaps as failures requiring review.

## Gate for adding a pathway

Before expanding clinical scope, define and independently review:

1. Intended population, setting, applicability, exclusions, source/version, and
   relationship to urgent alternatives.
2. Required information, units, observation timing, missingness semantics, and
   what to do if any item is unknown or unavailable.
3. Expected behavior for conflicting input, multiple concerns, partial
   recognition, and outside-scope populations.
4. Imaging indication and override policy; no unconditional chest imaging.
5. Independent clinician annotations, disagreement adjudication, held-out cases,
   and subgroup denominators appropriate to the intended scope.
6. The meaning of completion and handoff, human review requirements, and an
   explicit acceptance decision with remaining limitations.

This phase supplies the initial baseline and exposes gaps. It does not grant
approval for a new disease-specific assessment or autonomous clinical use.
