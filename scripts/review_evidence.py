"""Read-only review report: python -m scripts.review_evidence proposed.json."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from src.core.evidence import Corpus, CORPUS_PATH
from src.core.evidence_review import compare_corpora


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('proposed', type=Path)
    parser.add_argument('--current', type=Path, default=CORPUS_PATH)
    args = parser.parse_args()
    try:
        before, after = args.current.read_bytes(), args.proposed.read_bytes()
        report = compare_corpora(Corpus.model_validate_json(before), Corpus.model_validate_json(after),
                                 datetime.now(timezone.utc).date())
        report.update(current_sha256=hashlib.sha256(before).hexdigest(), proposed_sha256=hashlib.sha256(after).hexdigest())
    except (OSError, ValueError) as exc:
        report = {'valid': False, 'errors': [str(exc)]}
    print(json.dumps(report, indent=2))
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
