# Phase 16A: offline recovery boundaries

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 DEBUG=false CHECKPOINT_BACKEND=memory \
venv/bin/python -m scripts.evaluate_recovery
```

The command runs the fixed recovery/versioned-approval modules, captures JUnit
outcomes and writes `docs/evaluation/recovery-report.json`. A skipped, failed or
erroring test fails the gate. The report includes Python version, test source hashes,
backend identity and explicit flags for untested PostgreSQL/concurrency/clinical
claims. The synthetic provider never invokes a live model.

## Exercised boundaries

- A new service/graph can read the same in-process checkpoint and retain the loaded
  review version. This is reconstruction, not a process restart.
- Loss of the saver prevents approval even when persisted application results exist.
  Review returns a recovery-required conflict instead of an empty package.
- Loss of a checkpoint does not consume a pending clinical response in application
  storage. No inference is made from a stored result to reconstruct executable state.
- Repeated resolution of the same request returns HTTP 409 without resuming again.
  This covers sequential retries, not simultaneous request races.
- Explicit PostgreSQL initialization failures raise rather than silently using
  memory. Existing implicit development fallback remains unchanged.
- The Phase 15 tests cover owner access, exact loaded-version approval, evidence
  changes, reassessment, recorded identity/version and duplicate approval rejection.

Observed: nine gate tests passed; the broader selected regression suite passed 445
cases and the strict synthetic workflow suite passed 51/51 cases. One existing
Starlette TestClient deprecation warning remains. No frontend code changed.

## Required Phase 16B experiments

Use a disposable PostgreSQL database and explicitly verify the saver type before
recording any persistence result. Restart the application process while preserving
only database storage at each interruption point. Test pending questionnaire,
resolved response, urgent acknowledgement, evidence judgment and approval states.

Inject failure between application-record commits, checkpoint writes, graph resume
and result synchronization. Verify that retries neither invent completion nor lose
responses. A failure after a commit must be distinguished from a failure before it.
The application database and checkpointer currently do not share an atomic unit of
work; these experiments must precede any recovery guarantee.

For concurrency, coordinate two independent service processes with barriers, not
sleep timing: duplicate response submissions, two approvals of one version, and
approval racing with evidence review or reevaluation. Expected behavior must be
specified before the test: one accepted transition, explicit conflict for the
loser, and no approval referring to superseded outputs. Current optimistic version
checks do not establish this property. Shared serialization/transaction design is
still outstanding, as is duplicate audit-row handling.

## Independent clinical evaluation preparation

Keep developer regression labels separate from independent judgments. Freeze and
hash the evaluated artifact and case set; record intended populations and settings.
Have independent clinicians annotate applicability, urgency, missing information,
handoff, imaging and medication coverage without seeing model outputs or developer
expected answers. Record provenance, reviewer qualifications, disagreements and
adjudication separately. Reserve held-out cases and report subgroup denominators.

For simulated workspace evaluation, prespecify tasks, completion criteria, review
comprehension, question burden and override reasons. Record errors and incomplete
sessions, not only successful tasks. This document is a proposed protocol, not a
claim that reviewers, participants, ethics determinations or clinical outcomes
already exist. Acceptance criteria and study governance require clinical partners.
