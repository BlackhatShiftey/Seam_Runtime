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

from benchmarks.external.common.judge import build_judge
from benchmarks.external.common.runner import run_benchmark_parallel
from benchmarks.external.common.types import BenchmarkCase, ConversationTurn

EXPECTED_CATEGORIES = [
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "multi-session",
    "knowledge-update",
    "temporal-reasoning",
]
EXPECTED_TOTAL_QUESTIONS = 500


def _load_longmemeval_cases(dataset_path: str) -> list[BenchmarkCase]:
    """Parse a LongMemEval JSON dataset into case dicts.

    Supports the official cleaned LongMemEval release shape:
      {"question_id": str, "question_type": str, "question": str, "answer": str,
       "haystack_dates": [str], "haystack_sessions": [[{"role": str, "content": str}]]}

    Also supports the earlier local synthetic shape:
      {"sample_id": str, "conversation": [{"speaker": str, "text": str, ...}],
       "qa": [{"question": str, "gold_answer": str, "category": str}]}
    """
    with open(dataset_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    cases: list[BenchmarkCase] = []
    for index, sample in enumerate(raw):
        if "question_id" in sample and "haystack_sessions" in sample:
            cases.append(_official_case(sample, index))
            continue

        sid = sample["sample_id"]
        conversation = tuple(
            ConversationTurn(
                speaker=str(turn.get("speaker", turn.get("role", ""))),
                text=str(turn.get("text", turn.get("content", ""))),
                timestamp=turn.get("timestamp"),
            )
            for turn in sample.get("conversation", [])
        )
        for qi, qa in enumerate(sample.get("qa", [])):
            cases.append(
                BenchmarkCase(
                    case_id=f"{sid}::q{qi}",
                    question=str(qa["question"]),
                    gold_answer=str(qa.get("answer", qa.get("gold_answer", ""))),
                    category=str(qa.get("category", "unknown")),
                    conversation=conversation,
                )
            )
    return cases


def _official_case(sample: dict, index: int) -> BenchmarkCase:
    dates = sample.get("haystack_dates", [])
    turns: list[ConversationTurn] = []
    for session_index, session in enumerate(sample.get("haystack_sessions", [])):
        timestamp = dates[session_index] if session_index < len(dates) else None
        for turn in session:
            turns.append(
                ConversationTurn(
                    speaker=str(turn.get("role", turn.get("speaker", ""))),
                    text=str(turn.get("content", turn.get("text", ""))),
                    timestamp=timestamp,
                )
            )
    return BenchmarkCase(
        case_id=str(sample.get("question_id", f"longmemeval-{index}")),
        question=str(sample["question"]),
        gold_answer=str(sample.get("answer", "")),
        category=str(sample.get("question_type", "unknown")),
        conversation=tuple(turns),
    )


def _fixture_hash(cases) -> str:
    payload = json.dumps(
        [{"case_id": c.case_id, "question": c.question, "gold_answer": c.gold_answer}
         for c in cases],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dry_run_report(cases, dataset_path, judge_name):
    category_counts = Counter(c.category for c in cases)
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


def build_adapter(name: str):
    if name == "seam":
        from benchmarks.external.locomo.adapters.seam import SeamLocomoAdapter

        return SeamLocomoAdapter(db_path="test_seam/longmemeval")
    raise ValueError(f"unknown adapter {name!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LongMemEval benchmark runner for SEAM")
    parser.add_argument("--dataset-path", required=True, help="Path to LongMemEval JSON dataset")
    parser.add_argument("--output", help="Write JSON report to this path")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset and print counts without executing")
    parser.add_argument("--adapter", choices=["seam"], default="seam")
    parser.add_argument("--judge", choices=["none", "stub", "claude", "openai"], default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    if not Path(args.dataset_path).exists():
        print(f"ERROR: dataset not found: {args.dataset_path}", file=sys.stderr)
        print("Download LongMemEval from its public release and point --dataset-path to the JSON file.", file=sys.stderr)
        raise SystemExit(1)

    cases = _load_longmemeval_cases(args.dataset_path)
    if args.limit is not None:
        cases = cases[: args.limit]

    if args.dry_run:
        report = _dry_run_report(cases, args.dataset_path, args.judge)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["valid"] else 1)

    report = run_benchmark_parallel(
        adapter_factory=lambda: build_adapter(args.adapter),
        adapter_name=args.adapter,
        cases=cases,
        dataset_source=args.dataset_path,
        judge_factory=(
            lambda: build_judge(args.judge, model=args.judge_model)
            if args.judge is not None else None
        ),
        workers=args.workers,
    )
    report["benchmark"] = "longmemeval"

    report_json = json.dumps(report, indent=2, default=str)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report_json)
            f.write("\n")
        print(f"Report written to {args.output}")
    else:
        print(report_json)


if __name__ == "__main__":
    main()
