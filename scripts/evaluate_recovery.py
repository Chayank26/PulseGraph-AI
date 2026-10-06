"""Reproducible offline recovery-boundary report; never a clinical approval gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

TESTS = ['tests/test_recovery_boundaries.py', 'tests/test_versioned_approval.py', 'tests/test_projection_recovery.py']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/evaluation/recovery-report.json'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'DEBUG':'false', 'CHECKPOINT_BACKEND':'memory'}
    with tempfile.TemporaryDirectory(prefix='pulsegraph-recovery-') as directory:
        junit = Path(directory)/'results.xml'
        command = [sys.executable, '-m', 'pytest', *TESTS, '-q', '--junitxml='+str(junit)]
        process = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=120)
        cases = []
        if junit.exists():
            for case in ET.parse(junit).iter('testcase'):
                outcome = 'PASS'
                for tag, status in [('skipped','SKIPPED'),('failure','FAIL'),('error','ERROR')]:
                    if case.find(tag) is not None: outcome=status
                cases.append({'name':case.attrib['name'], 'outcome':outcome})
    passed = process.returncode == 0 and bool(cases) and all(c['outcome']=='PASS' for c in cases)
    report = {'generated_at':datetime.now(timezone.utc).isoformat(), 'python':platform.python_version(),
        'backend':'SQLite fixtures and in-memory checkpoints', 'provider':'synthetic',
        'clinical_validation':False, 'postgres_recovery_tested':False, 'concurrency_tested':False,
        'atomic_approval_established':False, 'gate_passed':passed, 'exit_code':process.returncode,
        'tests':cases, 'test_sha256':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in TESTS},
        'limitations':['Service reconstruction shares an in-process saver; it is not process-crash persistence.',
            'Lost-checkpoint tests prove refusal to proceed, not automatic recovery.',
            'Concurrent writes and checkpoint/application transaction failures require separate experiments.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'gate_passed':passed, 'total':len(cases), 'report':str(args.output)}))
    if not passed:
        print(process.stdout[-10000:]); print(process.stderr[-2000:])
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
