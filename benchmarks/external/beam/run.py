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
import ast
import hashlib
import json
import sys
from pathlib import Path

from benchmarks.external.common.judge import build_judge
from benchmarks.external.common.runner import run_benchmark_grouped_parallel
from benchmarks.external.common.types import BenchmarkCase, ConversationTurn

EXPECTED_BY_TRACK = {
    "1m": {"conversations": 35, "questions": 700},
    "10m": {"conversations": 10, "questions": 200},
}


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


def _load_beam_cases(dataset_path: str | Path) -> list[BenchmarkCase]:
    path = Path(dataset_path)
    if path.is_dir():
        return _load_beam_directory_cases(path)
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    rows = payload.get("rows", payload if isinstance(payload, list) else [])
    cases: list[BenchmarkCase] = []
    for row_index, item in enumerate(rows):
        row = item.get("row", item)
        conversation_id = str(row.get("conversation_id", f"conversation-{row_index}"))
        conversation = tuple(_iter_beam_turns(row.get("chat", [])))
        questions = _parse_probing_questions(row.get("probing_questions", {}))
        for category, category_questions in questions.items():
            for question_index, question_data in enumerate(category_questions):
                cases.append(
                    BenchmarkCase(
                        case_id=f"{conversation_id}::{category}::{question_index}",
                        conversation=conversation,
                        question=str(question_data.get("question", "")),
                        gold_answer=_beam_gold_answer(question_data),
                        category=str(category),
                    )
                )
    return cases


def _load_beam_directory_cases(root: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        qa_files = list(entry.glob("questions*.json")) + list(entry.glob("qa*.json"))
        conversation: tuple[ConversationTurn, ...] = ()
        for qf in qa_files:
            with qf.open("r", encoding="utf-8") as fh:
                qa_data = json.load(fh)
            questions = qa_data if isinstance(qa_data, list) else qa_data.get("questions", qa_data.get("qa", []))
            for question_index, question_data in enumerate(questions):
                cases.append(
                    BenchmarkCase(
                        case_id=f"{entry.name}::{question_data.get('category', 'unknown')}::{question_index}",
                        conversation=conversation,
                        question=str(question_data.get("question", "")),
                        gold_answer=_beam_gold_answer(question_data),
                        category=str(question_data.get("category", "unknown")),
                    )
                )
    return cases


def _iter_beam_turns(chat):
    for batch in chat:
        if isinstance(batch, dict):
            batch = [batch]
        for turn in batch:
            yield ConversationTurn(
                speaker=str(turn.get("role", turn.get("speaker", ""))),
                text=str(turn.get("content", turn.get("text", ""))),
                timestamp=turn.get("time_anchor"),
            )


def _parse_probing_questions(value):
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, dict):
        raise ValueError("BEAM probing_questions must parse to a dict")
    return parsed


def _beam_gold_answer(question_data: dict) -> str:
    for key in ("answer", "ideal_answer", "ideal_response", "ideal_summary", "expected_compliance"):
        value = question_data.get(key)
        if value:
            answer = str(value)
            break
    else:
        answer = ""
    rubric = question_data.get("rubric")
    if rubric:
        rubric_lines = "\n".join(f"- {item}" for item in rubric)
        return f"{answer}\nRubric:\n{rubric_lines}" if answer else f"Rubric:\n{rubric_lines}"
    return answer


def _dry_run_report(conversations, total_questions, dataset_path, track, judge_name):
    issues = []
    expected = EXPECTED_BY_TRACK.get(track, {})
    expected_conversations = expected.get("conversations")
    expected_questions = expected.get("questions")
    if expected_conversations is not None and len(conversations) != expected_conversations:
        issues.append(
            f"Expected {expected_conversations} conversations, found {len(conversations)}"
        )
    if expected_questions is not None and total_questions != expected_questions:
        issues.append(
            f"Expected {expected_questions} questions, found {total_questions}"
        )
    payload = json.dumps(conversations, sort_keys=True)
    fixture_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {
        "dataset_path": str(dataset_path),
        "benchmark": "beam",
        "track": track,
        "conversation_count": len(conversations),
        "expected_conversations": expected_conversations,
        "total_questions": total_questions,
        "expected_questions": expected_questions,
        "fixture_hash": fixture_hash,
        "estimated_judge_calls": total_questions if judge_name and judge_name not in ("none", "stub") else 0,
        "judge": judge_name or "none",
        "mode": "dry-run",
        "valid": len(issues) == 0,
        "validation_issues": issues,
    }


def _conversation_summary_from_cases(cases: list[BenchmarkCase]) -> tuple[list[dict], int]:
    counts: dict[str, int] = {}
    for case in cases:
        scope = _beam_scope_id(case)
        counts[scope] = counts.get(scope, 0) + 1
    conversations = [
        {"dir": scope, "question_count": count}
        for scope, count in sorted(counts.items())
    ]
    return conversations, len(cases)


def _beam_scope_id(case: BenchmarkCase) -> str:
    return case.case_id.split("::", 1)[0]


def build_adapter(name: str):
    if name == "seam":
        from benchmarks.external.locomo.adapters.seam import SeamLocomoAdapter

        return SeamLocomoAdapter(db_path="test_seam/beam", budget=4000)
    raise ValueError(f"unknown adapter {name!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BEAM benchmark runner for SEAM")
    parser.add_argument("--track", required=True, choices=["1m", "10m"],
                        help="BEAM track (10m is deferred)")
    parser.add_argument("--dataset-path", required=True, help="Path to BEAM dataset directory or Hugging Face rows JSON")
    parser.add_argument("--output", help="Write JSON report to this path")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset and print counts without executing")
    parser.add_argument("--adapter", choices=["seam"], default="seam")
    parser.add_argument("--judge", choices=["none", "stub", "claude", "openai"], default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        print(f"ERROR: BEAM dataset path not found: {args.dataset_path}", file=sys.stderr)
        print("Download BEAM from its public release and point --dataset-path to the dataset directory or rows JSON.", file=sys.stderr)
        raise SystemExit(1)

    cases = _load_beam_cases(dataset_path)
    if args.limit is not None:
        cases = cases[: args.limit]
    conversations, total_questions = _conversation_summary_from_cases(cases)

    if args.dry_run:
        report = _dry_run_report(conversations, total_questions, args.dataset_path, args.track, args.judge)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["valid"] else 1)

    report = run_benchmark_grouped_parallel(
        adapter_factory=lambda: build_adapter(args.adapter),
        adapter_name=args.adapter,
        cases=cases,
        scope_id=_beam_scope_id,
        dataset_source=args.dataset_path,
        judge_factory=(
            lambda: build_judge(args.judge, model=args.judge_model)
            if args.judge is not None else None
        ),
        workers=args.workers,
    )
    report["benchmark"] = "beam"
    report["track"] = args.track

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
