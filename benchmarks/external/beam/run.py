"""BEAM benchmark runner for SEAM.

BEAM evaluates memory over 100 conversations with 2,000 probing questions (1M track).
BEAM-10M is explicitly deferred and cannot be run accidentally.

Usage:
    python -m benchmarks.external.beam.run --track 1m --dataset-path /path/to/beam-dir --dry-run
    python -m benchmarks.external.beam.run --track 1m --dataset-path /path/to/beam-dir --output run.json

The full dataset is not bundled; point --dataset-path at a local BEAM release directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

BEAM_1M_EXPECTED_CONVERSATIONS = 100
BEAM_1M_EXPECTED_QUESTIONS = 2000


def _scan_beam_dataset(dataset_path: str, track: str):
    """Scan a BEAM dataset directory and return case metadata.

    BEAM datasets are directory-based. Each conversation is in a subdirectory
    with session files and a questions JSON file.
    """
    root = Path(dataset_path)
    if not root.is_dir():
        raise FileNotFoundError(f"BEAM dataset directory not found: {dataset_path}")

    conversations = []
    total_questions = 0

    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            qa_files = list(entry.glob("questions*.json")) + list(entry.glob("qa*.json"))
            conv_questions = 0
            for qf in qa_files:
                try:
                    with open(qf, "r", encoding="utf-8") as fh:
                        qa_data = json.load(fh)
                    if isinstance(qa_data, list):
                        conv_questions += len(qa_data)
                    elif isinstance(qa_data, dict):
                        conv_questions += len(qa_data.get("questions", qa_data.get("qa", [])))
                except Exception:
                    pass
            conversations.append({
                "dir": entry.name,
                "question_count": conv_questions,
            })
            total_questions += conv_questions

    return conversations, total_questions


def _dry_run_report(conversations, total_questions, dataset_path, track, judge_name):
    issues = []
    if track == "1m":
        if len(conversations) != BEAM_1M_EXPECTED_CONVERSATIONS:
            issues.append(
                f"Expected {BEAM_1M_EXPECTED_CONVERSATIONS} conversations, found {len(conversations)}"
            )
        if total_questions != BEAM_1M_EXPECTED_QUESTIONS:
            issues.append(
                f"Expected {BEAM_1M_EXPECTED_QUESTIONS} questions, found {total_questions}"
            )
    payload = json.dumps(conversations, sort_keys=True)
    fixture_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {
        "dataset_path": str(dataset_path),
        "benchmark": "beam",
        "track": track,
        "conversation_count": len(conversations),
        "expected_conversations": BEAM_1M_EXPECTED_CONVERSATIONS if track == "1m" else None,
        "total_questions": total_questions,
        "expected_questions": BEAM_1M_EXPECTED_QUESTIONS if track == "1m" else None,
        "fixture_hash": fixture_hash,
        "estimated_judge_calls": total_questions if judge_name and judge_name not in ("none", "stub") else 0,
        "judge": judge_name or "none",
        "mode": "dry-run",
        "valid": len(issues) == 0,
        "validation_issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="BEAM benchmark runner for SEAM")
    parser.add_argument("--track", required=True, choices=["1m", "10m"],
                        help="BEAM track (10m is deferred)")
    parser.add_argument("--dataset-path", required=True, help="Path to BEAM dataset directory")
    parser.add_argument("--output", help="Write JSON report to this path")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset and print counts without executing")
    parser.add_argument("--judge", choices=["none", "stub", "claude", "openai"], default=None)
    parser.add_argument("--judge-model", default=None)
    args = parser.parse_args()

    if args.track == "10m":
        print("ERROR: BEAM-10M is explicitly deferred.", file=sys.stderr)
        print("Large-scale BEAM-10M requires operator approval and a separate infra plan.", file=sys.stderr)
        print("Run with --track 1m for the standard 100-conversation / 2,000-question track.", file=sys.stderr)
        raise SystemExit(1)

    if not Path(args.dataset_path).is_dir():
        print(f"ERROR: BEAM dataset directory not found: {args.dataset_path}", file=sys.stderr)
        print("Download BEAM-1M from its public release and point --dataset-path to the dataset directory.", file=sys.stderr)
        raise SystemExit(1)

    conversations, total_questions = _scan_beam_dataset(args.dataset_path, args.track)

    if args.dry_run:
        report = _dry_run_report(conversations, total_questions, args.dataset_path, args.track, args.judge)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["valid"] else 1)

    print("Full BEAM runs require a judge adapter implementation.", file=sys.stderr)
    print("Currently only dry-run validation is supported.", file=sys.stderr)
    print("Run with --dry-run to validate dataset shape.", file=sys.stderr)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
