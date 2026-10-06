# Phase 16B3B: fail-stop checks for lost operation locks

Each serialized operation now has a guard with sticky failure state. For PostgreSQL,
it verifies that the dedicated connection is still valid, retains its original
backend PID and owns the expected advisory lock. Failure or an exception stops the
operation; the guard never reconnects, reacquires the lock or resumes old work.

The guard runs before ORM flush/commit, synchronous checkpoint put/put_writes/delete,
and return from the operation. Repository commits remain on their normal connection.
The graph temporarily uses a GuardedCheckpointer forwarding reads and serialization
to its actual saver. The captured guard also covers checkpoint writes on graph worker
threads; a mutex serializes probes on the dedicated connection. Guards are closed
when operations end so delayed writes cannot use an expired operation. Listeners and
the original graph saver are restored afterward. Failed operations roll back any
still-uncommitted application transaction. Already committed work is not undone.

Loss is reported as a workflow conflict without raw transport exception text. An
uncertain lock connection is discarded rather than returned to the pool. SQLite
uses the same write guard lifecycle with a local ownership probe; this adds no
cross-process SQLite guarantee. The adapter supports the current synchronous graph
service. Future async services need explicit async checkpoint-guard support.

## Verification

The selected regression suite passed 464 tests. Unit checks exercise permanent
failure, closed-guard rejection, checkpoint delegates not being called after loss,
application rollback and listener cleanup. The recovery runner includes these checks
and the existing session-serialization tests. No frontend change was required.

The live PostgreSQL probe uses a disposable pulsegraph_recovery_test database:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m scripts.evaluate_postgres_lock_loss
```

Set PULSEGRAPH_TEST_DATABASE_URL explicitly. The probe terminates the advisory-lock
backend from a separate administrative connection while the application worker
remains alive. It checks that the checkpoint guard refuses a write, the application
commit fails and rolls back its provisional insert, and a new operation can acquire
the released lock. The generated report records actual execution status. The probe
uses MemorySaver only as a guarded checkpoint delegate; separate PostgreSQL recovery
probes exercise the real PostgresSaver adapter. It accesses no clinical records.

## Not storage-level fencing

A successful ownership check and a following write still occur on different
connections. Lock loss can occur between them. These checks reduce the window for
undetected loss and stop work after detection; they do not eliminate stale writes
or make application/checkpoint persistence atomic. Writes outside the decorated
service methods are also outside this protection. Direct SQL execution is not
intercepted before every statement; ORM flush/commit and current graph writes are
covered. The probe must not be described as proof of fencing or exactly-once work.

The next increment needs a persistence design that validates a fencing generation
atomically with each write, or a supported shared transactional connection strategy,
including LangGraph pending writes/checkpoints and application records. It must
cover lock loss specifically between check and write, partial commits and fresh-worker
takeover. Mid-transition replay policies and independent clinical validation also
remain outstanding. Adding a token without enforcing it in every store is insufficient.

Phase 16B3C update: participating PostgreSQL application and checkpoint transactions
now lock/validate a durable ownership token inside each transaction, addressing the
check/write gap for those adapters. See `transaction-fencing.md` for deployment and
remaining cross-store/mixed-worker limitations. Earlier detection-only results above
remain historical verification of the preliminary guard.
