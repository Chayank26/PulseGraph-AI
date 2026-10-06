"""Opt-in stable-boundary workflow recovery across fresh Python processes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4


def worker(stage, identifier):
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session
    from langgraph.checkpoint.postgres import PostgresSaver
    from src.db.database import Base
    from src.db.models import DoctorModel, PatientModel
    from src.services.clinical_workflow import ClinicalWorkflowService
    from src.db.repositories.session_repository import SessionRepository
    url=make_url(os.environ['PULSEGRAPH_TEST_DATABASE_URL'])
    if url.get_backend_name()!='postgresql' or url.database!='pulsegraph_recovery_test':
        raise ValueError('A disposable PostgreSQL database named pulsegraph_recovery_test is required')
    engine=create_engine(url)
    Base.metadata.create_all(engine)
    conninfo=url.set(drivername='postgresql').render_as_string(hide_password=False)
    with PostgresSaver.from_conn_string(conninfo) as saver, Session(engine) as db:
        saver.setup()
        service=ClinicalWorkflowService(db,checkpointer=saver)
        # Corpus/model outputs are unnecessary for this incomplete-applicability handoff.
        if stage=='approval_seed':
            from src.core.state import ClinicianIdentity
            db.add(DoctorModel(doctor_id=identifier,full_name='Synthetic',department='Test',password_hash='unused'))
            db.add(PatientModel(patient_id=identifier,doctor_id=identifier,age=50,chief_complaint='back pain'))
            db.commit()
            service.sess_repo.create_session(identifier,identifier,identifier,identifier,
                intake_data={'pathway_decisions':{'low_back':'applicable'},
                             'imaging_decision':{'decision':'no_imaging','reason':'Synthetic clinician decision'}})
            service.run_session(identifier)
            request=service.sess_repo.get_pending_data_requests(identifier)[0]
            service.resolve_data_request(identifier,request.request_id,
                {'back_review_scope':'confirmed','back_review_serious_cause':'not_suspected'},reviewing_doctor_id=identifier)
            version=service.review_package(identifier,identifier)['review_version']
            def fail(*args, **kwargs): raise RuntimeError('injected approval interruption')
            service.graph.invoke=fail
            try:
                service.approve_session(identifier,ClinicianIdentity(doctor_id=identifier,full_name='Synthetic',department='Test'),review_version=version)
            except RuntimeError as exc:
                if str(exc)!='injected approval interruption': raise
            else: raise AssertionError('Approval fault was not reached')
        elif stage=='approval_recover':
            from src.services.clinical_workflow import WorkflowConflictError
            from src.core.state import ClinicianIdentity
            prior=service.review_package(identifier,identifier)
            assert prior['recovery_required'] and not prior['can_approve']
            assert service.recover_session(identifier,identifier)['recovery']=='FRESH_REVIEW_REQUIRED'
            current=service.review_package(identifier,identifier)
            assert current['review_version']!=prior['review_version']
            assert current['can_approve'] and current['approval'] is None
            identity=ClinicianIdentity(doctor_id=identifier,full_name='Synthetic',department='Test')
            try: service.approve_session(identifier,identity,review_version=prior['review_version'])
            except WorkflowConflictError: pass
            else: raise AssertionError('Old version was accepted')
            assert service.approve_session(identifier,identity,review_version=current['review_version'])['status']=='APPROVED'
        elif stage=='approval_verify':
            assert service.recover_session(identifier,identifier)['status']=='APPROVED'
            audit=service.sess_repo.get_audit_logs(identifier)
            assert sum(row.action=='INTERRUPTED_APPROVAL_RESET' for row in audit)==1
            assert sum(row.action=='EHR_PACKAGE_EXPORT' for row in audit)==1
            service.recover_session(identifier,identifier)
            assert len(service.sess_repo.get_audit_logs(identifier))==len(audit)
            assert service.sess_repo.get_cds_result(identifier).clinician_approval['approved'] is True
        elif stage=='seed_failure':
            db.add(DoctorModel(doctor_id=identifier,full_name='Synthetic',department='Test',password_hash='unused'))
            db.add(PatientModel(patient_id=identifier,doctor_id=identifier,age=50,chief_complaint='shortness of breath'))
            db.commit()
            service.sess_repo.create_session(identifier,identifier,identifier,identifier)
            def fail(**kwargs): raise RuntimeError('injected result write failure')
            service.sess_repo.save_cds_result=fail
            try: service.run_session(identifier)
            except RuntimeError as exc:
                if str(exc)!='injected result write failure': raise
            else: raise AssertionError('Failure injection was not reached')
            assert service.sess_repo.get_cds_result(identifier) is None
        elif stage=='recover_pending':
            assert service.recover_session(identifier,identifier)['status']=='WAITING_FOR_CLINICAL_DATA'
            requests=service.sess_repo.get_pending_data_requests(identifier)
            assert len(requests)==1
            count=len(service.sess_repo.get_audit_logs(identifier))
            service.recover_session(identifier,identifier)
            assert len(service.sess_repo.get_audit_logs(identifier))==count
            request=requests[0]
            original=service._sync_audit_and_results
            calls=0
            def fail_final(*args):
                nonlocal calls
                calls+=1
                if calls==2: raise RuntimeError('injected final projection failure')
                return original(*args)
            service._sync_audit_and_results=fail_final
            try:
                service.resolve_data_request(identifier,request.request_id,
                    {f['field_key']:'unknown' for f in request.required_fields},reviewing_doctor_id=identifier)
            except RuntimeError as exc:
                if str(exc)!='injected final projection failure': raise
            else: raise AssertionError('Final failure injection was not reached')
        elif stage=='recover_terminal':
            assert service.recover_session(identifier,identifier)['status']=='REQUIRES_CLINICIAN_ASSESSMENT'
            assert service.sess_repo.get_pending_data_requests(identifier)==[]
            count=len(service.sess_repo.get_audit_logs(identifier))
            service.recover_session(identifier,identifier)
            assert len(service.sess_repo.get_audit_logs(identifier))==count
            assert service.sess_repo.get_cds_result(identifier).final_status=='REQUIRES_CLINICIAN_ASSESSMENT'
    engine.dispose()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['seed_failure','recover_pending','recover_terminal','approval_seed','approval_recover','approval_verify'])
    parser.add_argument('--identifier')
    parser.add_argument('--scenario',choices=['projection','approval'],default='projection')
    parser.add_argument('--output',type=Path,default=Path('docs/evaluation/postgres-recovery-report.json'))
    args=parser.parse_args()
    if args.stage:
        worker(args.stage,args.identifier);return 0
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'gate_passed':False,'backend':'PostgresSaver + PostgreSQL',
        'clinical_validation':False,'mid_transition_replay_tested':False,'lock_loss_fencing_tested':False,
        'stages':[]}
    if 'PULSEGRAPH_TEST_DATABASE_URL' not in os.environ:
        report['status']='NOT_RUN_DATABASE_NOT_SUPPLIED'
    else:
        identifier='RECOVERY-'+uuid4().hex
        env={**os.environ,'DEBUG':'false','CHECKPOINT_BACKEND':'memory','DIAGNOSTIC_BACKEND':'disabled','PYTHONDONTWRITEBYTECODE':'1'}
        stages = ('approval_seed','approval_recover','approval_verify') if args.scenario == 'approval' else ('seed_failure','recover_pending','recover_terminal')
        report['scenario']=args.scenario
        for stage in stages:
            result=subprocess.run([sys.executable,'-m','scripts.evaluate_postgres_recovery','--stage',stage,'--identifier',identifier],
                env=env,capture_output=True,text=True,timeout=90)
            report['stages'].append({'stage':stage,'exit_code':result.returncode})
            if result.returncode:
                print(result.stderr[-3000:]);break
        report['gate_passed']=len(report['stages'])==3 and all(s['exit_code']==0 for s in report['stages'])
        report['status']='PASS' if report['gate_passed'] else 'FAIL'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'gate_passed':report['gate_passed']}))
    return 0 if report['gate_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
