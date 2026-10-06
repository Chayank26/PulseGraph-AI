"""PostgreSQL ownership checks held until the same transaction's commit/rollback."""
from sqlalchemy import text

IDENTITY_SQL = 'SELECT current_database(), inet_server_addr()::text, inet_server_port(), pg_postmaster_start_time()::text'
FENCE_SQL = 'SELECT token FROM public.workflow_operation_fences WHERE session_id = :session_id FOR SHARE'


def verify_fence(connection, session_id, token):
    from src.services.session_lock import WorkflowConflictError
    actual = connection.execute(text(FENCE_SQL), {'session_id':session_id}).scalar()
    if actual != token:
        raise WorkflowConflictError('Operation ownership changed. This worker cannot write; reload the session.')
