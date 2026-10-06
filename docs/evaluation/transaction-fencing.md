# Phase 16B3C: transaction-level operation fencing

Advisory locking still controls admission. Each admitted PostgreSQL operation now
assigns a fresh random token to its durable workflow_operation_fences row. The token
update is committed before the operation begins. An old application transaction
holds a shared lock on that row until commit/rollback; a replacement cannot update
the token until the old transaction ends. Takeover waits at most two seconds before
returning a conflict. Session operations must start without pending ORM changes.
Existing pre-operation read transactions are rolled back before attaching the fence.

Application Session transactions acquire the row FOR SHARE and verify the token in
after_begin. Thus token validation and the ensuing application writes occur in the
same database transaction. Repository commits release the shared row lock; every
new transaction validates again. At operation end, leftover read transactions are
rolled back so they cannot block later ownership changes.

FencedPostgresSaver wraps each synchronous cursor operation in an explicit PostgreSQL
transaction. Within that transaction it verifies database identity and acquires the
same shared row lock before accessing checkpoint tables. The inherited checkpoint,
blob and pending-write SQL therefore runs behind that transaction's ownership check.
The adapter does not use the underlying saver's pipeline path. External pipelines,
non-PostgresSaver delegates and mismatched PostgreSQL database identities are refused.
Previous sticky lock-loss checks remain as early detection, not the source of the
transaction-level guarantee.

## Deployment requirement

This change adds migration d36b951af825, following c25a840fe714. Before restarting a
PostgreSQL-backed application, apply the migration against the intended configured
database:

```sh
DEBUG=false CHECKPOINT_BACKEND=postgres venv/bin/alembic upgrade head
```

Configure the application and synchronous PostgresSaver to use the same PostgreSQL
database/public schema. An application using PostgreSQL can no longer execute these
workflow operations with a development MemorySaver fallback. SQLite remains supported
for isolated in-process tests and has no cross-process fencing guarantee. All workers
must use the new protocol; mixed old/new workers or direct SQL writers are outside
its protection. Existing application/development data was not migrated during this
implementation. Offline migration SQL generation passed; disposable probes created
the new schema from ORM metadata.

The adapter uses the installed PostgresSaver cursor/internal-connection API. Dependency
upgrades must rerun PostgreSQL fencing/recovery probes before deployment. This is
synchronous support only. Fence rows remain after operations; do not delete/reset rows
while a worker may still reference them. Retention cleanup needs its own protocol.

## Verified boundaries

The selected suite passed 468 tests and the recovery gate passed 32 checks. Real
PostgreSQL probes verified:

- A successful ownership probe followed immediately by backend termination and
  replacement-owner activation cannot authorize an old application write.
- The same injected check/write gap rejects old checkpoint pending writes, using the
  real FencedPostgresSaver; no checkpoint write row is created.
- An application transaction already holding the fence prevents takeover until it
  ends. The replacement returns a conflict on timeout and can retry afterward.
- Both three-process projection and interrupted-approval recovery probes still pass
  through real PostgresSaver transactions.

Results are recorded in postgres-fencing-report.json and the refreshed recovery
reports. Testing used a disposable PostgreSQL 16 container; no clinical dataset or
live model was involved. The test container was stopped and removed.

## Remaining limits

This prevents stale-token writes through the participating Session/saver transaction
boundaries. It is not one atomic transaction across the entire workflow: several
valid application/checkpoint commits may still precede a crash. Recovery from those
partial commits remains necessary. The deterministic race probe uses separate live
database connections with a coordinated injection; it is not an exhaustive scheduler
or full application-worker race study. Direct writes bypassing these adapters are
not fenced. No clinical validation, external EHR exactly-once delivery or automatic
mid-transition replay guarantee is established.

Next work: coordinated full-service process races and additional mid-transition
recovery policies, followed by independent clinical/human-factors evaluation.
