"""PostgresSaver cursor transactions share-lock and verify the operation fence."""
from contextlib import contextmanager
from langgraph.checkpoint.postgres import PostgresSaver, _internal
from psycopg.rows import dict_row
from src.services.write_fence import IDENTITY_SQL
from src.services.session_lock import WorkflowConflictError


class FencedPostgresSaver(PostgresSaver):
    def __init__(self, delegate, guard):
        if not isinstance(delegate, PostgresSaver) or delegate.pipe is not None:
            raise WorkflowConflictError('PostgreSQL fencing requires a synchronous PostgresSaver without an external pipeline.')
        super().__init__(delegate.conn, serde=delegate.serde)
        self.guard = guard

    @contextmanager
    def _cursor(self, *, pipeline=False):
        # Do not reuse PostgresSaver's pipeline path: checking and writing must be
        # in one explicit transaction, including put_writes and blob operations.
        with self.lock, _internal.get_connection(self.conn) as connection:
            self.guard.check()
            with connection.transaction(), connection.cursor(binary=True, row_factory=dict_row) as cursor:
                cursor.execute(IDENTITY_SQL)
                if tuple(cursor.fetchone().values()) != self.guard.database_identity:
                    raise WorkflowConflictError('Checkpoint and application fencing must use the same PostgreSQL database.')
                cursor.execute('SELECT token FROM public.workflow_operation_fences WHERE session_id = %s FOR SHARE',
                               (self.guard.session_id,))
                row = cursor.fetchone()
                if not row or row['token'] != self.guard.token:
                    raise WorkflowConflictError('Checkpoint operation ownership changed; write refused.')
                yield cursor
