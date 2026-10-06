"""Exercise ownership loss after a successful check, before each persistence write."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from langgraph.checkpoint.postgres import PostgresSaver
from src.services.session_lock import session_operation, WorkflowConflictError
from src.core.fenced_checkpointer import FencedPostgresSaver


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('docs/evaluation/postgres-fencing-report.json'))
    args=parser.parse_args()
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'gate_passed':False,
        'cross_store_atomic_transaction':False,'independent_clinical_validation':False,'checks':[]}
    url=os.environ.get('PULSEGRAPH_TEST_DATABASE_URL')
    if not url:
        report['status']='NOT_RUN_DATABASE_NOT_SUPPLIED'
    else:
        engine=create_engine(url)
        if engine.dialect.name!='postgresql' or engine.url.database!='pulsegraph_recovery_test':
            raise ValueError('Use only the disposable pulsegraph_recovery_test PostgreSQL database')
        os.environ['DEBUG'] = 'false'
        from src.db.models import WorkflowOperationFenceModel
        WorkflowOperationFenceModel.__table__.create(engine,checkfirst=True)
        conninfo=engine.url.set(drivername='postgresql').render_as_string(hide_password=False)
        table='fence_probe_'+uuid4().hex
        def terminate_owner(key):
            unsigned=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big')
            with engine.begin() as admin:
                pid=admin.execute(text("SELECT pid FROM pg_locks WHERE locktype='advisory' AND granted AND classid::bigint=:hi AND objid::bigint=:lo AND objsubid=1"),
                    {'hi':unsigned>>32,'lo':unsigned&0xffffffff}).scalar_one()
                assert admin.execute(text('SELECT pg_terminate_backend(:pid)'),{'pid':pid}).scalar()
        try:
            with engine.begin() as conn:conn.execute(text(f'CREATE TABLE {table} (value INTEGER)'))
            with PostgresSaver.from_conn_string(conninfo) as saver:
                saver.setup()
                for target in ('application','checkpoint'):
                    key='fence-'+uuid4().hex
                    refused=False; took_over=[]
                    with Session(engine) as db:
                        try:
                            with session_operation(db,key) as guard:
                                original_probe=guard.probe
                                def race():
                                    healthy=original_probe()
                                    if healthy and not took_over:
                                        # Deterministic injection in the check/write gap.
                                        terminate_owner(key)
                                        with Session(engine) as replacement:
                                            with session_operation(replacement,key):pass
                                        took_over.append(True)
                                    return healthy
                                guard.probe=race
                                if target=='application':
                                    db.execute(text(f'INSERT INTO {table} VALUES (1)'))
                                    db.commit()
                                else:
                                    FencedPostgresSaver(saver,guard).put_writes(
                                        {'configurable':{'thread_id':key,'checkpoint_ns':'','checkpoint_id':'probe'}},
                                        [('probe',1)], 'task')
                        except WorkflowConflictError:refused=True
                    assert refused and took_over
                    with engine.connect() as conn:
                        assert conn.execute(text(f'SELECT count(*) FROM {table}')).scalar()==0
                        assert conn.execute(text('SELECT count(*) FROM checkpoint_writes WHERE thread_id=:key'),{'key':key}).scalar()==0
                    report['checks'].append(target+'_stale_write_refused_after_successful_probe_and_takeover')
                key='held-transaction-'+uuid4().hex
                with Session(engine) as db:
                    try:
                        with session_operation(db,key):
                            db.execute(text('SELECT 1'))  # after_begin holds fence row FOR SHARE
                            terminate_owner(key)
                            blocked=False
                            with Session(engine) as replacement:
                                try:
                                    with session_operation(replacement,key):pass
                                except WorkflowConflictError:blocked=True
                            assert blocked
                            db.rollback()
                            with Session(engine) as replacement:
                                with session_operation(replacement,key):pass
                            report['checks'].append('takeover_waits_for_old_transaction_to_end')
                    except WorkflowConflictError:pass  # Original owner detects terminated connection.
                assert len(report['checks'])==3
            report.update(status='PASS',gate_passed=True)
        except Exception as exc:
            report.update(status='FAIL',error_type=type(exc).__name__)
        finally:
            with engine.begin() as conn:conn.execute(text(f'DROP TABLE IF EXISTS {table}'))
            engine.dispose()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'gate_passed':report['gate_passed']}))
    return 0 if report['gate_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
