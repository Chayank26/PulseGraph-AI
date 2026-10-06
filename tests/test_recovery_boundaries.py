"""Offline failure boundaries; these are not PostgreSQL crash/concurrency tests."""
import pytest
from langgraph.checkpoint.memory import MemorySaver
from src.core import checkpointer
from config.settings import settings
from test_triage_foundation import client
from test_optional_imaging import start, decision


def test_explicit_postgres_failure_never_falls_back(monkeypatch):
    import psycopg_pool
    monkeypatch.setattr(checkpointer, '_GLOBAL_CHECKPOINTER', None)
    monkeypatch.setattr(checkpointer, '_GLOBAL_DB_POOL', None)
    monkeypatch.setattr(settings, 'environment', 'development')
    def unavailable(*args, **kwargs):
        raise RuntimeError('Injected unavailable checkpoint transport')
    monkeypatch.setattr(psycopg_pool, 'ConnectionPool', unavailable)
    with pytest.raises(RuntimeError):
        checkpointer.get_default_checkpointer(force_backend='postgres')
    assert checkpointer._GLOBAL_CHECKPOINTER is None


def test_lost_checkpoint_cannot_approve_persisted_package(client, monkeypatch):
    path=start(client,decision('no_imaging'))
    version=client.get(path+'/review').json()['review_version']
    before=client.get(path+'/results').json()
    monkeypatch.setattr(checkpointer, '_GLOBAL_CHECKPOINTER', MemorySaver())
    assert client.get(path+'/review').status_code==409
    assert client.post(path+'/approve',json={'review_version':version}).status_code==409
    assert client.get(path+'/results').json()==before


def test_lost_checkpoint_does_not_consume_pending_response(client, monkeypatch):
    created=client.post('/api/clinical/sessions',json={'patient_id':'P'})
    path='/api/clinical/sessions/'+created.json()['session_id']
    client.post(path+'/run')
    before=client.get(path+'/data-requests').json()
    req=before[0]
    monkeypatch.setattr(checkpointer, '_GLOBAL_CHECKPOINTER', MemorySaver())
    response=client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{
        field['field_key']:'unknown' for field in req['required_fields']}})
    assert response.status_code==409
    assert client.get(path+'/data-requests').json()==before


def test_duplicate_response_does_not_resume_twice(client):
    created=client.post('/api/clinical/sessions',json={'patient_id':'P'})
    path='/api/clinical/sessions/'+created.json()['session_id']
    client.post(path+'/run')
    req=client.get(path+'/data-requests').json()[0]
    endpoint=path+'/data-requests/'+req['request_id']+'/resolve'
    data={'response_data':{field['field_key']:'unknown' for field in req['required_fields']}}
    assert client.post(endpoint,json=data).status_code==200
    before=client.get(path+'/results').json()
    assert client.post(endpoint,json=data).status_code==409
    assert client.get(path+'/results').json()==before


def test_service_reconstruction_retains_review_version(client):
    # Each request constructs a new service/graph over the same in-memory saver.
    path=start(client,decision('no_imaging'))
    first=client.get(path+'/review').json()
    second=client.get(path+'/review').json()
    assert first['review_version']==second['review_version']
    assert second['can_approve']
    assert client.post(path+'/approve',json={'review_version':first['review_version']}).status_code==200
