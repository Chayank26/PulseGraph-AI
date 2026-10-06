# Phase 16B3A: interrupted approval returns to fresh review

The recovery endpoint now recognizes two narrowly defined approval interruptions:
approval intent saved while the graph is at human_review, and approval saved with
ehr_export as the next node. Recovery requires the session owner, an attributable
approval record, and a diagnostic input fingerprint matching the current state.
Missing attribution, stale input, and other internal transitions remain conflicts.

Recovery does not invoke the graph. It writes a new checkpoint positioned before
human_review, clears active approval and reevaluation flags, and appends an
INTERRUPTED_APPROVAL_RESET event containing the prior approval record. It then
reconciles application status and clears application completion/approval timestamps.
Prior audit history is retained; the recovery event does not assert that the prior
clinical judgment was wrong. It records that the software approval did not complete.

The checkpoint change produces a new review version. An interrupted package is
ineligible for approval until recovered, and old versions are rejected afterward.
The clinician must load and review the new package and approve again. The workspace
shows a recovery explanation and an explicit owner-operated return-to-review action.
Completed terminal approvals are synchronized without resetting them.

If projection writing fails after the recovery checkpoint is written, a repeated
recovery synchronizes the same checkpoint without adding another reset event or
changing the version again. Anonymous approval flags lacking an approval record
remain refused. No database migration is required.

## Verification

457 selected regression tests and the frontend production build passed. Focused
checks cover both interruption points, stale review versions, completed approval,
repeat recovery and failure after the reset checkpoint. The recovery-gate runner
includes these tests. This is software verification, not clinical validation or a
browser interaction study.

The PostgreSQL runner supports a separate approval scenario:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m scripts.evaluate_postgres_recovery \
  --scenario approval --output docs/evaluation/postgres-approval-recovery-report.json
```

Supply PULSEGRAPH_TEST_DATABASE_URL for the disposable pulsegraph_recovery_test
database. Three fresh processes create a synthetic review, inject failure after
approval intent is checkpointed, recover/review/approve a new version, then verify
terminal approval and audit deduplication. Model generation is disabled in this
scenario. The report records actual execution status.

## Limits

The export node currently has no external delivery side effects. This reset policy
must be re-evaluated before adding real EHR delivery; a crashed side-effecting export
would need a delivery receipt/idempotency protocol, not blind replay or reset.

Other mid-transition checkpoints still require operator handling. The application
and checkpoint stores are not atomic, and advisory-lock connection loss still lacks
fencing. Phase 16B3B must address those boundaries and full service-process races.
Independent clinical annotations and usability studies also remain outstanding.
