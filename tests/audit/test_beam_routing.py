"""Tests for BEAM benchmark routing and dry-run validation."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _make_beam_dataset_dir(base_dir: str, conversation_count: int = 3):
    """Build a minimal BEAM-shaped dataset directory for validation testing."""
    root = Path(base_dir)
    for i in range(conversation_count):
        conv_dir = root / f"conv_{i:04d}"
        conv_dir.mkdir()
        qa_file = conv_dir / "questions.json"
        qa_file.write_text(json.dumps([
            {"question": f"Q{j} for conv {i}", "answer": f"A{j}", "category": "factual"}
            for j in range(5)
        ]))
    return root


class TestBeamRouting:
    def test_dry_run_scans_dataset_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_beam_dataset_dir(tmp, conversation_count=3)
            result = subprocess.run(
                [sys.executable, "-m", "benchmarks.external.beam.run",
                 "--track", "1m", "--dataset-path", tmp, "--dry-run"],
                capture_output=True, text=True, timeout=30,
            )
            report = json.loads(result.stdout)
            assert report["mode"] == "dry-run"
            assert report["conversation_count"] == 3
            assert report["total_questions"] == 15
            assert isinstance(report["fixture_hash"], str)
            assert report["valid"] is False  # not 100 conversations / 2000 questions

    def test_beam_10m_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-m", "benchmarks.external.beam.run",
                 "--track", "10m", "--dataset-path", tmp, "--dry-run"],
                capture_output=True, text=True, timeout=30,
            )
            assert result.returncode != 0
            assert "deferred" in result.stderr.lower()

    def test_missing_dataset_directory_errors(self):
        result = subprocess.run(
            [sys.executable, "-m", "benchmarks.external.beam.run",
             "--track", "1m", "--dataset-path", "/nonexistent/beam-dir", "--dry-run"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode != 0

    def test_dry_run_reports_expected_scale(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_beam_dataset_dir(tmp, conversation_count=5)
            result = subprocess.run(
                [sys.executable, "-m", "benchmarks.external.beam.run",
                 "--track", "1m", "--dataset-path", tmp, "--dry-run"],
                capture_output=True, text=True, timeout=30,
            )
            report = json.loads(result.stdout)
            assert report["expected_conversations"] == 100
            assert report["expected_questions"] == 2000

    def test_seam_cli_routes_beam_1m_dataset_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_beam_dataset_dir(tmp, conversation_count=3)
            result = subprocess.run(
                [
                    sys.executable, "-m", "seam", "bench", "external", "beam",
                    "--track", "1m", "--dataset-path", tmp, "--dry-run", "--format", "json",
                ],
                capture_output=True, text=True, timeout=30,
            )
            assert result.returncode != 2, result.stderr
            report = json.loads(result.stdout)
            assert report["mode"] == "dry-run"
            assert report["conversation_count"] == 3
            assert report["valid"] is False
