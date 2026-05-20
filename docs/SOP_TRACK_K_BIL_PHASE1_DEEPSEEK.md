# SOP — Track K BIL Phase 1 (BIL-0..BIL-2 benchmark bundles), DeepSeek Execution Pass

Issued: 2026-05-19 (post HISTORY#213)
Owner pattern: Codex authors and verifies; DeepSeek executes all items in
sequence in a single session; Codex reviews the full diff at handback,
appends HISTORY entries, rebuilds derived history/stream state, writes a
snapshot, runs gates, and commits.

Scope: implement the first Track K benchmark-integrity slice without
guessing signing identity, transparency-log policy, or independent rerun
policy. This SOP implements **BIL-0 through BIL-2 only**:

- BIL-0: raw benchmark result, no SEAM integrity envelope
- BIL-1: benchmark result hash
- BIL-2: benchmark result hash plus deterministic input manifest hash

Out of scope for this SOP:

- BIL-3 signed bundles
- BIL-4 audit hash-chain linkage
- BIL-5 external transparency log
- BIL-6 independent reproducible rerun
- CI baseline source selection for `seam benchmark gate --baseline`
- live LLM judge calls
- changing existing benchmark scores, runner semantics, or datasets

## Why this slice

Track I external benchmarks already produce LoCoMo results and optional
LLM-judge scores. Track K says those results must eventually be sealed at
the highest supported Benchmark Integrity Level. The first useful step is
to make result files independently inspectable and verifiable with a
deterministic bundle envelope. That can be tested locally without keys,
network access, or policy decisions.

## Hard rules

1. Read this SOP once before touching code.
2. Do not read all of `HISTORY.md`. Use `PROJECT_STATUS.md`,
   `HISTORY_INDEX.md`, and bounded context packs only if needed.
3. Write failing tests first for each item. Confirm RED before runtime
   edits. Then make the smallest implementation.
4. Do not edit `HISTORY.md`, `HISTORY_INDEX.md`, `PROJECT_STATUS.md`,
   `REPO_LEDGER.md`, `.seam/`, `.github/workflows/`, `archive/`,
   `docs/archive/`, `build/`, `.venv/`, `test_seam/`, or
   `experimental/webui/`.
5. Do not stage, commit, or push. Codex reviews and commits.
6. Do not call live LLM providers. Stub judge only.
7. Do not introduce top-level imports of optional `anthropic`, `openai`,
   `mem0`, or `zep` packages.
8. Do not promote LLM judge scores into deterministic benchmark gates.
   BIL seals the evidence file; it does not make probabilistic judging a
   hard gate.

## Pre-flight

Run once before starting:

```bash
git status --short
git branch --show-current
git log --oneline -1
python -m pytest test_seam_all/ tools/history/ tools/streams/ tests/ -q
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
python -m tools.streams.verify_streams
```

Expected starting state when this SOP was written:

- Branch: `main`
- Dirty files: 0
- Latest commit subject after Codex closeout: `Add Track K BIL Phase 1 DeepSeek SOP`
- Full active suite: 405 passed, 3 skipped, 3 subtests passed
- Four SEAM gates: OK

If the worktree is dirty, STOP and emit `SCOPE_LIMIT_HIT` with reason
`ambiguous_owner`.

## Per-item gate

After each item:

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py -q
python -m py_compile seam.py
python -m compileall -q seam_runtime benchmarks tools scripts installers
```

After the final item:

```bash
python -m pytest test_seam_all/ tools/history/ tools/streams/ tests/ -q
python -m seam bench external --quickstart locomo --adapter seam --judge stub --output /tmp/seam-locomo-bil-result.json
python -m seam bench seal /tmp/seam-locomo-bil-result.json --level BIL-2 --output /tmp/seam-locomo-bil-bundle.json
python -m seam bench verify /tmp/seam-locomo-bil-bundle.json --format json
python -m seam bench inspect /tmp/seam-locomo-bil-bundle.json --format json
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
python -m tools.streams.verify_streams
```

## Files

Create:

- `seam_runtime/benchmark_integrity.py` — pure-Python BIL envelope,
  hashing, sealing, inspection, and verification helpers
- `test_seam_all/test_benchmark_integrity.py` — unit and CLI tests

Modify:

- `seam_runtime/cli.py` — add `seam bench inspect`, `seam bench seal`,
  and `seam bench verify`

Do not modify benchmark runner scoring code unless a test proves the new
integrity module cannot consume the existing report shape.

## Bundle contract

Use this bundle shape exactly for Phase 1:

```json
{
  "version": "SEAM-BENCHMARK-BUNDLE/1",
  "bil": {
    "level": "BIL-2",
    "result_hash": "<sha256>",
    "input_manifest_hash": "<sha256-or-null>"
  },
  "result": {},
  "input_manifest": {}
}
```

Use canonical JSON for every hash:

```python
json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

No timestamps in the BIL hash inputs. A timestamp may be added later under
signing/audit policy, but not in this deterministic Phase 1 bundle.

`input_manifest` for external LoCoMo-style results must include:

```json
{
  "version": "SEAM-BENCHMARK-INPUT-MANIFEST/1",
  "benchmark": "locomo",
  "adapter": "seam",
  "dataset": {"source": "...", "case_count": 10},
  "case_count": 10,
  "case_ids": ["..."],
  "judge": {
    "present": true,
    "judge_names": ["stub"],
    "judge_models": ["stub-1"]
  }
}
```

For internal `SEAM-BENCH/1` results, the manifest may use `run_id`,
`requested_suite`, `executed_suites`, `fixture_scope`, and family/case
identifiers instead of external `benchmark`/`adapter` fields.

## Task BIL1 — Pure integrity module

**Files:**

- Create: `seam_runtime/benchmark_integrity.py`
- Create/modify test: `test_seam_all/test_benchmark_integrity.py`

### Step 1: Write failing tests

Create `test_seam_all/test_benchmark_integrity.py` with these tests first:

```python
from __future__ import annotations

import copy
import json
import subprocess
import sys

import pytest

from seam_runtime.benchmark_integrity import (
    BUNDLE_VERSION,
    inspect_benchmark_integrity,
    seal_benchmark_bundle,
    verify_benchmark_bundle,
)


def _external_result() -> dict:
    return {
        "version": "SEAM-EXTERNAL-MEMORY-BENCHMARK-RESULT/1",
        "benchmark": "locomo",
        "adapter": "seam",
        "dataset": {"source": "quickstart", "case_count": 2},
        "run_started_at": "2026-05-19T00:00:00+00:00",
        "elapsed_seconds": 0.12,
        "scores": {"context_recall_mean": 1.0, "answer_em_mean": 1.0, "answer_f1_mean": 1.0},
        "cases": [
            {
                "case_id": "case-b",
                "category": "synthetic",
                "scores": {"context_recall": 1.0, "answer_em": 1.0, "answer_f1": 1.0},
                "judge": {"verdict": "correct", "score": 1.0, "judge_name": "stub", "judge_model": "stub-1"},
            },
            {
                "case_id": "case-a",
                "category": "synthetic",
                "scores": {"context_recall": 1.0, "answer_em": 1.0, "answer_f1": 1.0},
                "judge": {"verdict": "correct", "score": 1.0, "judge_name": "stub", "judge_model": "stub-1"},
            },
        ],
        "integrity_hash": "existing-runner-hash",
    }


def test_seal_bil2_external_result_has_manifest_and_hashes():
    bundle = seal_benchmark_bundle(_external_result(), level="BIL-2")

    assert bundle["version"] == BUNDLE_VERSION
    assert bundle["bil"]["level"] == "BIL-2"
    assert len(bundle["bil"]["result_hash"]) == 64
    assert len(bundle["bil"]["input_manifest_hash"]) == 64
    assert bundle["input_manifest"]["benchmark"] == "locomo"
    assert bundle["input_manifest"]["adapter"] == "seam"
    assert bundle["input_manifest"]["case_ids"] == ["case-a", "case-b"]
    assert bundle["input_manifest"]["judge"]["present"] is True
    assert bundle["input_manifest"]["judge"]["judge_names"] == ["stub"]
    assert bundle["input_manifest"]["judge"]["judge_models"] == ["stub-1"]


def test_seal_bil1_has_no_input_manifest_hash():
    bundle = seal_benchmark_bundle(_external_result(), level="BIL-1")

    assert bundle["bil"]["level"] == "BIL-1"
    assert len(bundle["bil"]["result_hash"]) == 64
    assert bundle["bil"]["input_manifest_hash"] is None
    assert bundle["input_manifest"] is None


def test_verify_bundle_detects_result_tamper():
    bundle = seal_benchmark_bundle(_external_result(), level="BIL-2")
    tampered = copy.deepcopy(bundle)
    tampered["result"]["scores"]["answer_em_mean"] = 0.0

    report = verify_benchmark_bundle(tampered)

    assert report["status"] == "FAIL"
    assert any(check["id"] == "result_hash" and check["status"] == "FAIL" for check in report["checks"])


def test_verify_bundle_detects_manifest_tamper():
    bundle = seal_benchmark_bundle(_external_result(), level="BIL-2")
    tampered = copy.deepcopy(bundle)
    tampered["input_manifest"]["case_ids"].append("case-z")

    report = verify_benchmark_bundle(tampered)

    assert report["status"] == "FAIL"
    assert any(check["id"] == "input_manifest_hash" and check["status"] == "FAIL" for check in report["checks"])


def test_inspect_raw_result_reports_bil0():
    report = inspect_benchmark_integrity(_external_result())

    assert report["status"] == "PASS"
    assert report["bil"]["level"] == "BIL-0"
    assert report["bil"]["sealed"] is False
    assert len(report["bil"]["computed_result_hash"]) == 64


def test_inspect_bundle_reports_bil2_verified():
    bundle = seal_benchmark_bundle(_external_result(), level="BIL-2")

    report = inspect_benchmark_integrity(bundle)

    assert report["status"] == "PASS"
    assert report["bil"]["level"] == "BIL-2"
    assert report["bil"]["sealed"] is True
    assert report["verification"]["status"] == "PASS"


def test_unknown_bil_level_rejected():
    with pytest.raises(ValueError, match="unsupported BIL level"):
        seal_benchmark_bundle(_external_result(), level="BIL-3")
```

Run:

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py -q
```

Expected: FAIL because `seam_runtime.benchmark_integrity` does not exist.

### Step 2: Implement `seam_runtime/benchmark_integrity.py`

Create the module with:

```python
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

BUNDLE_VERSION = "SEAM-BENCHMARK-BUNDLE/1"
INPUT_MANIFEST_VERSION = "SEAM-BENCHMARK-INPUT-MANIFEST/1"
SUPPORTED_BIL_LEVELS = {"BIL-0", "BIL-1", "BIL-2"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json_payload(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return copy.deepcopy(source)
    path = Path(source)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_payload(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def result_hash(result: dict[str, Any]) -> str:
    return sha256_canonical(result)


def build_input_manifest(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("version") == "SEAM-EXTERNAL-MEMORY-BENCHMARK-RESULT/1":
        cases = result.get("cases") or []
        case_ids = sorted(str(case.get("case_id")) for case in cases if case.get("case_id") is not None)
        judge_entries = [case.get("judge") for case in cases if isinstance(case.get("judge"), dict)]
        judge_names = sorted(
            {str(entry.get("judge_name")) for entry in judge_entries if entry.get("judge_name") is not None}
        )
        judge_models = sorted(
            {str(entry.get("judge_model")) for entry in judge_entries if entry.get("judge_model") is not None}
        )
        return {
            "version": INPUT_MANIFEST_VERSION,
            "benchmark": result.get("benchmark"),
            "adapter": result.get("adapter"),
            "dataset": copy.deepcopy(result.get("dataset") or {}),
            "case_count": len(cases),
            "case_ids": case_ids,
            "judge": {
                "present": bool(judge_entries),
                "judge_names": judge_names,
                "judge_models": judge_models,
            },
        }
    if result.get("version") == "SEAM-BENCH/1":
        families = result.get("families") or {}
        family_cases: dict[str, list[str]] = {}
        for family_name, family in families.items():
            cases = family.get("cases") if isinstance(family, dict) else []
            family_cases[str(family_name)] = sorted(
                str(case.get("case_id") or case.get("id") or case.get("name"))
                for case in cases or []
                if isinstance(case, dict)
            )
        return {
            "version": INPUT_MANIFEST_VERSION,
            "benchmark": "seam-internal",
            "run_id": result.get("run_id"),
            "requested_suite": result.get("requested_suite"),
            "executed_suites": list(result.get("executed_suites") or []),
            "fixture_scope": result.get("fixture_scope"),
            "families": family_cases,
        }
    return {
        "version": INPUT_MANIFEST_VERSION,
        "benchmark": result.get("benchmark") or result.get("version") or "unknown",
        "case_count": len(result.get("cases") or []),
        "case_ids": sorted(
            str(case.get("case_id") or case.get("id"))
            for case in result.get("cases") or []
            if isinstance(case, dict) and (case.get("case_id") or case.get("id"))
        ),
    }


def seal_benchmark_bundle(result: dict[str, Any], *, level: str = "BIL-2") -> dict[str, Any]:
    if level not in SUPPORTED_BIL_LEVELS or level == "BIL-0":
        raise ValueError(f"unsupported BIL level for sealing: {level}")
    result_copy = copy.deepcopy(result)
    manifest = build_input_manifest(result_copy) if level == "BIL-2" else None
    return {
        "version": BUNDLE_VERSION,
        "bil": {
            "level": level,
            "result_hash": result_hash(result_copy),
            "input_manifest_hash": sha256_canonical(manifest) if manifest is not None else None,
        },
        "result": result_copy,
        "input_manifest": manifest,
    }


def verify_benchmark_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    status = "PASS"
    if bundle.get("version") != BUNDLE_VERSION:
        return {
            "version": "SEAM-BENCHMARK-BUNDLE-VERIFY/1",
            "status": "FAIL",
            "bil": {"level": "BIL-0", "sealed": False},
            "checks": [{"id": "bundle_version", "status": "FAIL", "message": "not a SEAM benchmark bundle"}],
        }
    bil = bundle.get("bil") or {}
    level = bil.get("level")
    result = bundle.get("result")
    if level not in {"BIL-1", "BIL-2"}:
        checks.append({"id": "bil_level", "status": "FAIL", "message": f"unsupported level {level!r}"})
    else:
        checks.append({"id": "bil_level", "status": "PASS", "message": ""})
    if not isinstance(result, dict):
        checks.append({"id": "result", "status": "FAIL", "message": "bundle result must be an object"})
    else:
        actual = result_hash(result)
        expected = bil.get("result_hash")
        checks.append({
            "id": "result_hash",
            "status": "PASS" if actual == expected else "FAIL",
            "expected": expected,
            "actual": actual,
            "message": "" if actual == expected else "result hash mismatch",
        })
    if level == "BIL-2":
        manifest = bundle.get("input_manifest")
        if not isinstance(manifest, dict):
            checks.append({"id": "input_manifest", "status": "FAIL", "message": "BIL-2 requires input_manifest object"})
        else:
            actual = sha256_canonical(manifest)
            expected = bil.get("input_manifest_hash")
            checks.append({
                "id": "input_manifest_hash",
                "status": "PASS" if actual == expected else "FAIL",
                "expected": expected,
                "actual": actual,
                "message": "" if actual == expected else "input manifest hash mismatch",
            })
    for check in checks:
        if check.get("status") != "PASS":
            status = "FAIL"
    return {
        "version": "SEAM-BENCHMARK-BUNDLE-VERIFY/1",
        "status": status,
        "bil": {
            "level": level or "BIL-0",
            "sealed": True,
            "result_hash": bil.get("result_hash"),
            "input_manifest_hash": bil.get("input_manifest_hash"),
        },
        "checks": checks,
    }


def inspect_benchmark_integrity(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("version") == BUNDLE_VERSION:
        verification = verify_benchmark_bundle(payload)
        return {
            "version": "SEAM-BENCHMARK-INTEGRITY-INSPECT/1",
            "status": verification["status"],
            "bil": verification["bil"],
            "verification": verification,
        }
    return {
        "version": "SEAM-BENCHMARK-INTEGRITY-INSPECT/1",
        "status": "PASS",
        "bil": {
            "level": "BIL-0",
            "sealed": False,
            "computed_result_hash": result_hash(payload),
            "input_manifest": build_input_manifest(payload),
        },
        "verification": None,
    }
```

### Step 3: Run focused tests

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py -q
```

Expected: PASS for the module tests.

## Task BIL2 — CLI commands

**Files:**

- Modify: `seam_runtime/cli.py`
- Modify: `test_seam_all/test_benchmark_integrity.py`

### Step 1: Add failing CLI tests

Append these tests:

```python
def test_cli_bench_seal_verify_inspect_roundtrip(tmp_path):
    result_path = tmp_path / "result.json"
    bundle_path = tmp_path / "bundle.json"
    result_path.write_text(json.dumps(_external_result()), encoding="utf-8")

    seal = subprocess.run(
        [
            sys.executable,
            "-m",
            "seam",
            "bench",
            "seal",
            str(result_path),
            "--level",
            "BIL-2",
            "--output",
            str(bundle_path),
        ],
        capture_output=True,
        text=True,
    )
    assert seal.returncode == 0, seal.stderr
    assert bundle_path.exists()

    verify = subprocess.run(
        [sys.executable, "-m", "seam", "bench", "verify", str(bundle_path), "--format", "json"],
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
    verify_payload = json.loads(verify.stdout)
    assert verify_payload["status"] == "PASS"
    assert verify_payload["bil"]["level"] == "BIL-2"

    inspect = subprocess.run(
        [sys.executable, "-m", "seam", "bench", "inspect", str(bundle_path), "--format", "json"],
        capture_output=True,
        text=True,
    )
    assert inspect.returncode == 0, inspect.stderr
    inspect_payload = json.loads(inspect.stdout)
    assert inspect_payload["bil"]["level"] == "BIL-2"
    assert inspect_payload["verification"]["status"] == "PASS"


def test_cli_bench_verify_fails_on_tampered_bundle(tmp_path):
    bundle = seal_benchmark_bundle(_external_result(), level="BIL-2")
    bundle["result"]["cases"][0]["scores"]["answer_f1"] = 0.0
    bundle_path = tmp_path / "tampered.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, "-m", "seam", "bench", "verify", str(bundle_path), "--format", "json"],
        capture_output=True,
        text=True,
    )

    assert verify.returncode == 1
    payload = json.loads(verify.stdout)
    assert payload["status"] == "FAIL"
    assert any(check["id"] == "result_hash" and check["status"] == "FAIL" for check in payload["checks"])
```

Run:

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py -q
```

Expected: FAIL because CLI subcommands are missing.

### Step 2: Modify `seam_runtime/cli.py`

Add imports near the existing benchmark imports:

```python
from .benchmark_integrity import (
    inspect_benchmark_integrity,
    load_json_payload,
    seal_benchmark_bundle,
    verify_benchmark_bundle as verify_integrity_bundle,
    write_json_payload,
)
```

Add subparsers under the existing `bench_parser` block:

```python
    bench_seal_parser = bench_subparsers.add_parser("seal", help="Seal a benchmark result as a BIL bundle")
    bench_seal_parser.add_argument("result", help="Benchmark result JSON path")
    bench_seal_parser.add_argument("--level", choices=["BIL-1", "BIL-2"], default="BIL-2")
    bench_seal_parser.add_argument("--output", required=True, help="Write sealed bundle JSON to this path")
    bench_seal_parser.add_argument("--format", choices=["pretty", "json"], default="pretty")

    bench_verify_parser = bench_subparsers.add_parser("verify", help="Verify a sealed benchmark BIL bundle")
    bench_verify_parser.add_argument("bundle", help="Benchmark bundle JSON path")
    bench_verify_parser.add_argument("--format", choices=["pretty", "json"], default="pretty")

    bench_inspect_parser = bench_subparsers.add_parser("inspect", help="Inspect benchmark integrity/BIL status")
    bench_inspect_parser.add_argument("payload", help="Benchmark result or bundle JSON path")
    bench_inspect_parser.add_argument("--format", choices=["pretty", "json"], default="pretty")
```

Add handling in `run_cli` before `runtime = SeamRuntime(args.db)`:

```python
    if args.command == "bench" and args.bench_command == "seal":
        result_payload = load_json_payload(args.result)
        bundle = seal_benchmark_bundle(result_payload, level=args.level)
        write_json_payload(args.output, bundle)
        report = inspect_benchmark_integrity(bundle)
        if args.format == "json":
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(_render_bil_integrity_pretty(report))
        return

    if args.command == "bench" and args.bench_command == "verify":
        bundle = load_json_payload(args.bundle)
        report = verify_integrity_bundle(bundle)
        if args.format == "json":
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(_render_bil_integrity_pretty({"status": report["status"], "bil": report["bil"], "verification": report}))
        raise SystemExit(0 if report.get("status") == "PASS" else 1)

    if args.command == "bench" and args.bench_command == "inspect":
        payload = load_json_payload(args.payload)
        report = inspect_benchmark_integrity(payload)
        if args.format == "json":
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(_render_bil_integrity_pretty(report))
        raise SystemExit(0 if report.get("status") == "PASS" else 1)
```

Add a helper near other render helpers in `cli.py`:

```python
def _render_bil_integrity_pretty(report: dict[str, object]) -> str:
    bil = report.get("bil") if isinstance(report.get("bil"), dict) else {}
    verification = report.get("verification") if isinstance(report.get("verification"), dict) else None
    lines = [
        f"SEAM benchmark integrity: {report.get('status')}",
        f"BIL: {bil.get('level')}",
        f"Sealed: {bil.get('sealed')}",
    ]
    if bil.get("result_hash"):
        lines.append(f"Result hash: {bil.get('result_hash')}")
    if bil.get("input_manifest_hash"):
        lines.append(f"Input manifest hash: {bil.get('input_manifest_hash')}")
    if verification:
        failed = [check for check in verification.get("checks", []) if check.get("status") != "PASS"]
        lines.append(f"Verification checks: {len(verification.get('checks', [])) - len(failed)}/{len(verification.get('checks', []))} passed")
        for check in failed[:10]:
            lines.append(f"- {check.get('id')}: {check.get('message')}")
    return "\n".join(lines)
```

### Step 3: Run focused tests

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py -q
```

Expected: PASS.

## Task BIL3 — Quickstart sealing smoke

**Files:**

- Modify: `test_seam_all/test_benchmark_integrity.py`

### Step 1: Add failing quickstart smoke

Append:

```python
def test_quickstart_stub_result_can_be_sealed_and_verified(tmp_path):
    result_path = tmp_path / "locomo-result.json"
    bundle_path = tmp_path / "locomo-bundle.json"

    quickstart = subprocess.run(
        [
            sys.executable,
            "-m",
            "seam",
            "bench",
            "external",
            "--quickstart",
            "locomo",
            "--adapter",
            "seam",
            "--judge",
            "stub",
            "--output",
            str(result_path),
        ],
        capture_output=True,
        text=True,
    )
    assert quickstart.returncode == 0, quickstart.stderr

    seal = subprocess.run(
        [
            sys.executable,
            "-m",
            "seam",
            "bench",
            "seal",
            str(result_path),
            "--level",
            "BIL-2",
            "--output",
            str(bundle_path),
        ],
        capture_output=True,
        text=True,
    )
    assert seal.returncode == 0, seal.stderr

    verify = subprocess.run(
        [sys.executable, "-m", "seam", "bench", "verify", str(bundle_path), "--format", "json"],
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
    payload = json.loads(verify.stdout)
    assert payload["status"] == "PASS"
    assert payload["bil"]["level"] == "BIL-2"
```

Run:

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py::test_quickstart_stub_result_can_be_sealed_and_verified -q
```

Expected after BIL1+BIL2 implementation: PASS. If it fails, fix only
the BIL module or CLI command wiring. Do not change LoCoMo scoring.

## Task BIL4 — Documentation

**Files:**

- Modify: `benchmarks/external/README.md`
- Modify: `docs/roadmap/TRUST_SECURITY_AUDITABILITY.md`

### Step 1: Update external benchmark README

Add a short section after the quickstart examples:

```markdown
## Benchmark Integrity Levels

External benchmark results can be sealed into deterministic SEAM benchmark
bundles:

```bash
seam bench external --quickstart locomo --adapter seam --judge stub --output locomo-result.json
seam bench seal locomo-result.json --level BIL-2 --output locomo.seam-bundle.json
seam bench verify locomo.seam-bundle.json
seam bench inspect locomo.seam-bundle.json
```

Current Track K support covers BIL-0 through BIL-2 only. BIL-3 signing,
BIL-4 audit-chain linkage, BIL-5 transparency logs, and BIL-6 independent
reruns require operator policy decisions and are not implemented yet.
LLM judge scores remain informational; sealing records the evidence but
does not make probabilistic judge scores a deterministic gate.
```

### Step 2: Update roadmap status note

In `docs/roadmap/TRUST_SECURITY_AUDITABILITY.md`, under F13, add:

```markdown
Phase 1 implementation note: current implementation supports BIL-0
through BIL-2 for benchmark result files and external benchmark bundles.
BIL-3 through BIL-6 remain planned until signing identity,
audit-ledger linkage, transparency-log target, and independent-rerun
policy are decided.
```

## Final verification

Run:

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py -q
python -m pytest test_seam_all/ tools/history/ tools/streams/ tests/ -q
python -m py_compile seam.py
python -m compileall -q seam_runtime benchmarks tools scripts installers
python -m seam bench external --quickstart locomo --adapter seam --judge stub --output /tmp/seam-locomo-bil-result.json
python -m seam bench seal /tmp/seam-locomo-bil-result.json --level BIL-2 --output /tmp/seam-locomo-bil-bundle.json
python -m seam bench verify /tmp/seam-locomo-bil-bundle.json --format json
python -m seam bench inspect /tmp/seam-locomo-bil-bundle.json --format json
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
python -m tools.streams.verify_streams
git diff --check
```

Also scan the changed files for secrets/session links:

```bash
rg -n -i "(sk-proj-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[0-9A-Za-z_]{20,}|https://(chatgpt\\.com/share|chat\\.openai\\.com/share|claude\\.ai/share|gemini\\.google\\.com/share))" seam_runtime/benchmark_integrity.py seam_runtime/cli.py test_seam_all/test_benchmark_integrity.py benchmarks/external/README.md docs/roadmap/TRUST_SECURITY_AUDITABILITY.md
```

Expected: no matches.

## Final DeepSeek handoff format

Emit one block per completed task:

```text
===== DEEPSEEK REPORT: ITEM_SUCCESS =====
  item_id: BIL1
  item_title: Pure integrity module
  files_changed: [...]
  tests_added: [...]
  focused_test_cmd: ...
  focused_test_before_fix: FAIL (...)
  focused_test_after_fix: PASS (...)
  full_suite_result: PASS (...)
  compile_result: PASS (...)
  benchmark_smoke_result: PASS / N/A
  gates_result: PASS / N/A
  diff_stat: ...
  additional_observations: ...
  ready_for_next_item: yes / all_items_complete
===== END REPORT =====
```

If a stop condition fires:

```text
===== DEEPSEEK REPORT: SCOPE_LIMIT_HIT =====
  item_id: ...
  reason: ...
  command: ...
  observed: ...
  files_changed_so_far: [...]
  suggested_operator_decision: ...
===== END REPORT =====
```

Then STOP without staging, committing, or pushing.
