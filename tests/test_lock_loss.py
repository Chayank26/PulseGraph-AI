import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from langgraph.checkpoint.memory import MemorySaver
from src.services.session_lock import OperationGuard, guarded_writes, WorkflowConflictError
from src.core.guarded_checkpointer import GuardedCheckpointer


def test_loss_is_sticky_even_if_probe_becomes_healthy():
    healthy=[False]
    guard=OperationGuard(lambda:healthy[0])
    with pytest.raises(WorkflowConflictError):guard.check()
    healthy[0]=True
    with pytest.raises(WorkflowConflictError):guard.check()


@pytest.mark.parametrize('method',['put','put_writes','delete_thread'])
def test_checkpoint_mutations_refused_before_delegate(method,monkeypatch):
    saver=MemorySaver()
    calls=[]
    monkeypatch.setattr(saver,method,lambda *args,**kwargs:calls.append(args))
    guarded=GuardedCheckpointer(saver,OperationGuard(lambda:False))
    with pytest.raises(WorkflowConflictError):getattr(guarded,method)('ignored')
    assert calls==[]


def test_failed_probe_rolls_back_commit_and_removes_listeners():
    engine=create_engine('sqlite://')
    with engine.begin() as conn:conn.execute(text('CREATE TABLE probe (value INTEGER)'))
    healthy=[True]
    guard=OperationGuard(lambda:healthy[0])
    with Session(engine) as db:
        with pytest.raises(WorkflowConflictError):
            with guarded_writes(db,guard):
                db.execute(text('INSERT INTO probe VALUES (1)'))
                healthy[0]=False
                db.commit()
        assert db.execute(text('SELECT count(*) FROM probe')).scalar()==0
        db.commit()  # Listener belongs only to the operation, not the pooled session.
    engine.dispose()


def test_closed_guard_rejects_late_writes():
    guard=OperationGuard()
    guard.check();guard.close()
    with pytest.raises(WorkflowConflictError):guard.check()


def test_probe_exception_becomes_conflict_without_error_details():
    def broken():raise RuntimeError('sensitive transport details')
    with pytest.raises(WorkflowConflictError,match='Session lock was lost') as error:
        OperationGuard(broken).check()
    assert 'sensitive' not in str(error.value)
