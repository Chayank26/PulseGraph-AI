"""Terminate a dedicated lock backend and verify fail-stop write guards, not fencing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from langgraph.checkpoint.memory import MemorySaver
from src.core.guarded_checkpointer import GuardedCheckpointer
from src.services.session_lock import session_operation, WorkflowConflictError


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('docs/evaluation/postgres-lock-loss-report.json'))
    args=parser.parse_args()
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'gate_passed':False,
        'storage_level_fencing':False,'atomic_check_and_write':False,'checks':[]}
    url=os.environ.get('PULSEGRAPH_TEST_DATABASE_URL')
    if not url:
        report['status']='NOT_RUN_DATABASE_NOT_SUPPLIED'
    else:
        engine=create_engine(url)
        if engine.dialect.name!='postgresql' or engine.url.database!='pulsegraph_recovery_test':
            raise ValueError('Use a disposable PostgreSQL database named pulsegraph_recovery_test')
        key='loss-probe-'+uuid4().hex
        unsigned=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big')
        table='loss_probe_'+uuid4().hex  # Generated identifier, never user input.
        try:
            with engine.begin() as conn:conn.execute(text(f'CREATE TABLE {table} (value INTEGER)'))
            blocked=False
            with Session(engine) as db:
                try:
                    with session_operation(db,key) as guard:
                        db.execute(text(f'INSERT INTO {table} VALUES (1)'))
                        with engine.begin() as admin:
                            pid=admin.execute(text("SELECT pid FROM pg_locks WHERE locktype='advisory' AND granted AND classid::bigint=:hi AND objid::bigint=:lo AND objsubid=1"),
                                {'hi':unsigned>>32,'lo':unsigned&0xffffffff}).scalar_one()
                            assert admin.execute(text('SELECT pg_terminate_backend(:pid)'),{'pid':pid}).scalar()
                        try:GuardedCheckpointer(MemorySaver(),guard).put_writes({},[], 'probe')
                        except WorkflowConflictError:report['checks'].append('checkpoint_write_refused_after_lock_loss')
                        else:raise AssertionError('Checkpoint write accepted')
                        db.commit()
                except WorkflowConflictError:blocked=True
            assert blocked
            with engine.connect() as conn:assert conn.execute(text(f'SELECT count(*) FROM {table}')).scalar()==0
            report['checks'].append('application_commit_refused_and_rolled_back')
            with Session(engine) as replacement:
                with session_operation(replacement,key):pass
            report['checks'].append('new_operation_acquires_released_lock')
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
