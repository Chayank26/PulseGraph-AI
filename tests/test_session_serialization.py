"""Deterministic in-process concurrency checks; PostgreSQL tested separately."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.services.session_lock import session_operation, WorkflowConflictError, _LOCAL_LOCKS
from src.api.dependencies import get_db
from src.services.clinical_workflow import ClinicalWorkflowService
from test_triage_foundation import client
from test_optional_imaging import start, decision


def test_conflict_and_release_after_failure():
    engine=create_engine('sqlite://')
    entered=Event(); release=Event()
    def holder():
        with Session(engine) as db:
            with session_operation(db,'S'):
                entered.set()
                assert release.wait(5)
                raise RuntimeError('Injected failure')
    with ThreadPoolExecutor() as pool:
        future=pool.submit(holder)
        assert entered.wait(5)
        try:
            with Session(engine) as db:
                with pytest.raises(WorkflowConflictError):
                    with session_operation(db,'S'): pass
                with session_operation(db,'OTHER'): pass
        finally:
            release.set()
        with pytest.raises(RuntimeError): future.result(timeout=5)
    with Session(engine) as db:
        with session_operation(db,'S'): pass
    assert 'S' not in _LOCAL_LOCKS
    engine.dispose()


def test_mutation_conflicts_do_not_change_approval(client):
    path=start(client,decision('no_imaging'))
    version=client.get(path+'/review').json()['review_version']
    before=client.get(path+'/results').json()
    database=client.app.dependency_overrides[get_db]()
    db=next(database)
    try:
        with session_operation(db,path.rsplit('/',1)[1]):
            assert client.post(path+'/approve',json={'review_version':version}).status_code==409
            assert client.get(path+'/review').status_code==409
            assert client.post(path+'/reevaluate',json={'notes':'chest pain'}).status_code==409
            assert client.post(path+'/reject',json={}).status_code==409
        assert client.get(path+'/results').json()==before
        assert client.post(path+'/approve',json={'review_version':version}).status_code==200
    finally:
        database.close()
