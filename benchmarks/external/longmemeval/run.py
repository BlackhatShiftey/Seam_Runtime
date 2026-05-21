"""LongMemEval benchmark runner for SEAM.

LongMemEval evaluates long-context memory with 500 questions across 5 categories:
information extraction, multi-session reasoning, temporal reasoning, knowledge
updates, and abstention.

Usage:
    python -m benchmarks.external.longmemeval.run --dataset-path /path/to/longmemeval.json --dry-run
    python -m benchmarks.external.longmemeval.run --dataset-path /path/to/longmemeval.json --output run.json

The full dataset is not bundled; point --dataset-path at a local LongMemEval release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

EXPECTED_CATEGORIES = [
    "information_extraction",
    "multi_session_reasoning",
    "temporal_reasoning",
    "knowledge_updates",
    "abstention",
]
EXPECTED_TOTAL_QUESTIONS = 500


def _load_longmemeval_cases(dataset_path: str):
    """Parse a LongMemEval JSON dataset into case dicts.

    Expected shape per sample:
      {"sample_id": str, "conversation": [{"speaker": str, "text": str, ...}],
       "qa": [{"question": str, "gold_answer": str, "category": str}]}
    """
    with open(dataset_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    cases = []
    for sample in raw:
        sid = sample["sample_id"]
        for qi, qa in enumerate(sample.get("qa", [])):
            cases.append({
                "case_id": f"{sid}::q{qi}",
                "question": qa["question"],
                "gold_answer": qa.get("answer", qa.get("gold_answer", "")),
                "category": qa.get("category", "unknown"),
                "conversation": sample.get("conversation", []),
            })
    return cases


def _fixture_hash(cases) -> str:
    payload = json.dumps(
        [{"case_id": c["case_id"], "question": c["question"], "gold_answer": c["gold_answer"]}
         for c in cases],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dry_run_report(cases, dataset_path, judge_name):
    category_counts = Counter(c["category"] for c in cases)
    present_cats = set(category_counts.keys())
    missing_cats = [c for c in EXPECTED_CATEGORIES if c not in present_cats]
    issues = []
    if missing_cats:
        issues.append(f"Missing expected categories: {missing_cats}")
    if len(cases) != EXPECTED_TOTAL_QUESTIONS:
        issues.append(
            f"Expected {EXPECTED_TOTAL_QUESTIONS} questions, found {len(cases)}"
        )
    return {
        "dataset_path": str(dataset_path),
        "benchmark": "longmemeval",
        "case_count": len(cases),
        "expected_total": EXPECTED_TOTAL_QUESTIONS,
        "categories": dict(category_counts),
        "missing_categories": missing_cats,
        "fixture_hash": _fixture_hash(cases),
        "estimated_judge_calls": len(cases) if judge_name and judge_name not in ("none", "stub") else 0,
        "judge": judge_name or "none",
        "mode": "dry-run",
        "valid": len(issues) == 0,
        "validation_issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="LongMemEval benchmark runner for SEAM")
    parser.add_argument("--dataset-path", required=True, help="Path to LongMemEval JSON dataset")
    parser.add_argument("--output", help="Write JSON report to this path")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset and print counts without executing")
    parser.add_argument("--judge", choices=["none", "stub", "claude", "openai"], default=None)
    parser.add_argument("--judge-model", default=None)
    args = parser.parse_args()

    if not Path(args.dataset_path).exists():
        print(f"ERROR: dataset not found: {args.dataset_path}", file=sys.stderr)
        print("Download LongMemEval from its public release and point --dataset-path to the JSON file.", file=sys.stderr)
        raise SystemExit(1)

    cases = _load_longmemeval_cases(args.dataset_path)

    if args.dry_run:
        report = _dry_run_report(cases, args.dataset_path, args.judge)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["valid"] else 1)

    print("Full LongMemEval runs require a judge adapter implementation.", file=sys.stderr)
    print("Currently only dry-run validation is supported.", file=sys.stderr)
    print("Run with --dry-run to validate dataset shape.", file=sys.stderr)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
