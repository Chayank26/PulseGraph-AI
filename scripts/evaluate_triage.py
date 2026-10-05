"""Run with: DEBUG=false CHECKPOINT_BACKEND=memory venv/bin/python -m scripts.evaluate_triage"""
import argparse
import json
import logging
from pathlib import Path
from src.evaluation.triage import DEFAULT_CASES, load_cases, evaluate, markdown_report


def main():
    parser = argparse.ArgumentParser(description='Offline synthetic triage regression and coverage report')
    parser.add_argument('--cases', type=Path, default=DEFAULT_CASES)
    parser.add_argument('--output', type=Path, default=Path('docs/evaluation/triage-report.json'))
    parser.add_argument('--require-no-known-gaps', action='store_true',
                        help='Also fail when a documented coverage gap remains')
    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR)
    report = evaluate(load_cases(args.cases), args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    args.output.with_suffix('.md').write_text(markdown_report(report))
    print(json.dumps({'total': report['total'], 'counts': report['counts'],
                      'regression_gate_passed': report['regression_gate_passed'], 'expansion_ready': False}))
    passed = report['regression_gate_passed'] and not (args.require_no_known_gaps and report['counts'].get('KNOWN_GAP'))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
