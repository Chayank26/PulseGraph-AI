# Phase 16B1: session serialization

Workflow run, clinical-response resolution, approval, reassessment, rejection,
evidence-judgment submission and versioned review reads now share a per-session
operation lock. On PostgreSQL this is a nonblocking advisory lock derived from the
session ID. A dedicated connection holds it for the whole operation, independently
of repository commits. A concurrent operation receives a conflict and must reload.
Different sessions use different keys. Failed unlocks invalidate the connection so
it cannot return to the pool with an uncertain lock state.

SQLite uses a process-local lock registry only for development and isolated tests.
Its entries are released after use. It is not a multi-worker SQLite locking solution.
The decorator preserves method signatures and expires cached ORM data after lock
acquisition. Approval validates the displayed version while holding the lock;
evidence writes and reassessment cannot interleave through these service methods.

## PostgreSQL probe

Use only a disposable test database, supplied in PULSEGRAPH_TEST_DATABASE_URL:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m scripts.evaluate_postgres_lock
```

The runner requires the PostgreSQL dialect; no fallback is allowed. A child process
holds the lock, commits its application Session and signals the parent through a
pipe. The parent verifies conflict on the same session and progress on another.
It terminates the holder and verifies that a new operation can acquire the lock.
No patient tables or project records are accessed. The JSON report distinguishes
these primitive checks from full workflow crash recovery. Missing configuration or
failed checks return nonzero, without storing database credentials in the report.

## Limits and next work

Serialization is not a shared atomic transaction for the application database and
graph checkpoints. A worker may die after one store commits and before the other;
the next worker must still detect/reconcile partially applied work. A lost dedicated
lock connection can release the database lock while application code is still
running, so connection-loss fencing requires a separate design and failure test.
Direct graph writes outside these services do not participate in the lock protocol.
Each operation also reserves an extra database connection; deployment pool sizing
must account for that connection alongside application and checkpoint activity.

Phase 16B2 remains: full PostgreSQL workflow restart and partial-commit injection,
approval/evidence and duplicate-response races across independent service processes,
reconciliation/fencing design, and idempotent audit persistence. Independent clinical
annotations and usability evaluation are separate outstanding work. No atomic
approval, automatic recovery or clinical safety claim follows from this lock probe.
