"""Serialize workflow operations per session across PostgreSQL application workers."""
from contextlib import contextmanager
from functools import wraps
import hashlib
from threading import Lock
from sqlalchemy import text


class WorkflowConflictError(ValueError):
    """The requested transition conflicts with current workflow state."""


_LOCAL_GUARD = Lock()
_LOCAL_LOCKS = {}


@contextmanager
def session_operation(db, session_id):
    engine = db.get_bind()
    if engine.dialect.name == 'postgresql':
        key = int.from_bytes(hashlib.sha256(session_id.encode()).digest()[:8], 'big', signed=True)
        # Dedicated connection: repository commits must not release the workflow lock.
        with engine.connect() as connection:
            acquired = connection.execute(text('SELECT pg_try_advisory_lock(:key)'), {'key':key}).scalar()
            if not acquired:
                raise WorkflowConflictError('Another operation is updating this session. Reload and retry.')
            try:
                db.expire_all()
                yield
            finally:
                try:
                    connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key':key})
                except Exception:
                    # Never return a possibly locked physical connection to the pool.
                    connection.invalidate()
                    raise
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
            yield
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
        with session_operation(workflow.db, session_id):
            return method(self, session_id, *args, **kwargs)
    return wrapped
