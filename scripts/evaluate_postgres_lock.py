"""Opt-in multiprocess advisory-lock probe using an explicitly supplied disposable database."""
import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.services.session_lock import session_operation, WorkflowConflictError


def holder(url, key, pipe):
    engine=create_engine(url)
    try:
        with Session(engine) as db, session_operation(db,key):
            db.commit()
            pipe.send('LOCKED_AFTER_COMMIT')
            if pipe.poll(20): pipe.recv()
    finally:
        engine.dispose()
        pipe.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('docs/evaluation/postgres-lock-report.json'))
    args=parser.parse_args()
    url=os.environ.get('PULSEGRAPH_TEST_DATABASE_URL')
    report={'generated_at':datetime.now(timezone.utc).isoformat(), 'backend':'postgresql',
        'gate_passed':False,'clinical_validation':False,'workflow_crash_recovery_tested':False,
        'atomic_database_checkpoint_transaction':False,'checks':[]}
    if not url:
        report['status']='NOT_RUN_DATABASE_NOT_SUPPLIED'
    else:
        engine=create_engine(url)
        if engine.dialect.name!='postgresql': raise ValueError('PostgreSQL is required; no fallback is permitted')
        key='pulsegraph-lock-probe-'+uuid4().hex
        context=mp.get_context('spawn'); parent,child=context.Pipe()
        process=context.Process(target=holder,args=(url,key,child))
        try:
            process.start(); child.close()
            if not parent.poll(30) or parent.recv()!='LOCKED_AFTER_COMMIT':
                raise RuntimeError('Lock-holder process did not become ready')
            with Session(engine) as db:
                try:
                    with session_operation(db,key): pass
                except WorkflowConflictError:
                    report['checks'].append('cross_process_conflict_after_repository_commit')
                else: raise RuntimeError('Concurrent lock was accepted')
                with session_operation(db,key+'-independent'): pass
                report['checks'].append('independent_session_progress')
            # Simulate abrupt worker death, not an application/checkpoint transaction recovery.
            process.terminate(); process.join(10)
            with Session(engine) as db:
                with session_operation(db,key): pass
            report['checks'].append('lock_released_after_worker_termination')
            report.update(status='PASS',gate_passed=True)
        except Exception as exc:
            report.update(status='FAIL',error_type=type(exc).__name__)
        finally:
            if process.is_alive(): process.terminate(); process.join(10)
            parent.close(); engine.dispose()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'gate_passed':report['gate_passed']}))
    return 0 if report['gate_passed'] else 1


if __name__=='__main__': raise SystemExit(main())
