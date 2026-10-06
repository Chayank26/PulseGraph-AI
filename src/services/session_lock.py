"""Serialize workflow operations per session across PostgreSQL application workers."""
from contextlib import contextmanager
from functools import wraps
import hashlib
from threading import Lock, RLock
from sqlalchemy import text, event
from uuid import uuid4
from src.services.write_fence import verify_fence, IDENTITY_SQL


class WorkflowConflictError(ValueError):
    """The requested transition conflicts with current workflow state."""


class OperationGuard:
    """A detected loss is sticky; it must never reacquire and continue old work."""
    def __init__(self, probe=lambda: True):
        self.probe = probe
        self.failed = False
        self.mutex = RLock()

    def check(self):
        with self.mutex:
            if not self.failed:
                try:
                    self.failed = not self.probe()
                except Exception:
                    self.failed = True
            if self.failed:
                raise WorkflowConflictError('Session lock was lost or operation ended. Stop and reload; recovery may be required.')

    def close(self):
        with self.mutex:
            self.failed = True


@contextmanager
def guarded_writes(db, guard):
    def check(*args, **kwargs):
        guard.check()
    event.listen(db, 'before_commit', check)
    event.listen(db, 'before_flush', check)
    try:
        guard.check()
        yield guard
        guard.check()
    except BaseException:
        db.rollback()
        raise
    finally:
        guard.close()
        event.remove(db, 'before_commit', check)
        event.remove(db, 'before_flush', check)


_LOCAL_GUARD = Lock()
_LOCAL_LOCKS = {}


@contextmanager
def session_operation(db, session_id):
    engine = db.get_bind()
    if engine.dialect.name == 'postgresql':
        key = int.from_bytes(hashlib.sha256(session_id.encode()).digest()[:8], 'big', signed=True)
        # Dedicated connection: repository commits must not release the workflow lock.
        with engine.connect() as connection:
            acquired, pid = connection.execute(text('SELECT pg_try_advisory_lock(:key), pg_backend_pid()'), {'key':key}).one()
            if not acquired:
                raise WorkflowConflictError('Another operation is updating this session. Reload and retry.')
            connection.commit()
            unsigned = key & ((1 << 64) - 1)
            def still_owned():
                if connection.closed or connection.invalidated:
                    return False
                return bool(connection.execute(text(
                    "SELECT pg_backend_pid() = :pid AND EXISTS (SELECT 1 FROM pg_locks "
                    "WHERE pid = pg_backend_pid() AND locktype = 'advisory' AND granted "
                    "AND classid::bigint = :hi AND objid::bigint = :lo AND objsubid = 1)"),
                    {'pid':pid, 'hi':unsigned >> 32, 'lo':unsigned & 0xffffffff}).scalar())
            guard = OperationGuard(still_owned)
            listener = None
            try:
                if db.new or db.dirty or db.deleted:
                    raise WorkflowConflictError('Start workflow operations without pending application changes.')
                db.rollback()  # Close any pre-operation read transaction before attaching the fence.
                guard.session_id = session_id
                guard.token = uuid4().hex
                guard.database_identity = tuple(connection.execute(text(IDENTITY_SQL)).one())
                connection.execute(text("SET LOCAL lock_timeout = '2s'"))
                try:
                    connection.execute(text(
                        'INSERT INTO public.workflow_operation_fences (session_id, token) VALUES (:session_id, :token) '
                        'ON CONFLICT (session_id) DO UPDATE SET token = EXCLUDED.token'),
                        {'session_id':session_id, 'token':guard.token})
                    connection.commit()
                except Exception as exc:
                    if getattr(getattr(exc, 'orig', None), 'sqlstate', None) == '55P03':
                        raise WorkflowConflictError('An older session transaction is still active; takeover must wait.') from exc
                    raise
                def listener(session, transaction, application_connection):
                    guard.check()
                    verify_fence(application_connection, session_id, guard.token)
                event.listen(db, 'after_begin', listener)
                db.expire_all()
                with guarded_writes(db, guard):
                    yield guard
            finally:
                # Read transactions also hold row locks; never leave one across operations.
                db.rollback()
                if listener is not None and event.contains(db, 'after_begin', listener):
                    event.remove(db, 'after_begin', listener)
                try:
                    connection.rollback()
                    if connection.closed or connection.invalidated:
                        connection.invalidate()
                    else:
                        connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key':key})
                except Exception:
                    # Preserve the original conflict; discard uncertain lock ownership.
                    connection.invalidate()
    elif engine.dialect.name == 'sqlite':
        # Isolated development/test support only, not cross-process serialization.
        with _LOCAL_GUARD:
            lock, users = _LOCAL_LOCKS.get(session_id, (Lock(), 0))
            _LOCAL_LOCKS[session_id] = (lock, users + 1)
        acquired = lock.acquire(blocking=False)
        try:
            if not acquired:
                raise WorkflowConflictError('Another operation is updating this session. Reload and retry.')
            db.expire_all()
            with guarded_writes(db, OperationGuard()) as guard:
                yield guard
        finally:
            if acquired:
                lock.release()
            with _LOCAL_GUARD:
                _, users = _LOCAL_LOCKS[session_id]
                if users == 1:
                    del _LOCAL_LOCKS[session_id]
                else:
                    _LOCAL_LOCKS[session_id] = (lock, users - 1)
    else:
        raise RuntimeError('Workflow serialization requires PostgreSQL or isolated SQLite tests.')


def serialized_session(method):
    @wraps(method)
    def wrapped(self, session_id, *args, **kwargs):
        workflow = getattr(self, 'workflow', self)
        from src.core.guarded_checkpointer import GuardedCheckpointer
        with session_operation(workflow.db, session_id) as guard:
            original = workflow.graph.checkpointer
            if hasattr(guard, 'token'):
                from src.core.fenced_checkpointer import FencedPostgresSaver
                workflow.graph.checkpointer = FencedPostgresSaver(original, guard)
            else:
                workflow.graph.checkpointer = GuardedCheckpointer(original, guard)
            try:
                return method(self, session_id, *args, **kwargs)
            finally:
                workflow.graph.checkpointer = original
    return wrapped
