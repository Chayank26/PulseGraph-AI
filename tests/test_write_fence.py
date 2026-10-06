from types import SimpleNamespace
import pytest
from langgraph.checkpoint.memory import MemorySaver
from src.core.fenced_checkpointer import FencedPostgresSaver
from src.services.write_fence import verify_fence
from src.services.session_lock import WorkflowConflictError


class Connection:
    def __init__(self, token):self.token=token;self.statements=[]
    def execute(self,statement,params):
        self.statements.append((str(statement),params))
        return SimpleNamespace(scalar=lambda:self.token)


@pytest.mark.parametrize('actual',[None,'old-token'])
def test_missing_or_superseded_token_is_rejected(actual):
    with pytest.raises(WorkflowConflictError):verify_fence(Connection(actual),'S','current-token')


def test_matching_token_is_locked_for_transaction():
    connection=Connection('current-token')
    verify_fence(connection,'S','current-token')
    assert 'FOR SHARE' in connection.statements[0][0]
    assert connection.statements[0][1]=={'session_id':'S'}


def test_postgres_workflow_cannot_use_memory_checkpoint_fallback():
    with pytest.raises(WorkflowConflictError):FencedPostgresSaver(MemorySaver(),object())
