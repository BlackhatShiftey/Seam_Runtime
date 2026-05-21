"""Tests for LongMemEval dataset routing and dry-run validation."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _make_minimal_longmemeval_dataset():
    """Build a minimal LongMemEval-shaped dataset for validation testing."""
    return [
        {
            "sample_id": "lme-1",
            "conversation": [
                {"speaker": "user", "text": "I need to schedule a meeting for next Tuesday at 3pm."},
                {"speaker": "assistant", "text": "I've added that to your calendar."},
            ],
            "qa": [
                {"question": "When is the meeting?", "answer": "Tuesday at 3pm", "category": "information_extraction"},
                {"question": "Did the assistant confirm?", "answer": "Yes, added to calendar", "category": "multi_session_reasoning"},
            ],
        },
        {
            "sample_id": "lme-2",
            "conversation": [
                {"speaker": "user", "text": "My birthday is March 15."},
                {"speaker": "user", "text": "Actually, I was wrong — it's March 16."},
            ],
            "qa": [
                {"question": "When is the user's birthday now?", "answer": "March 16", "category": "knowledge_updates"},
            ],
        },
    ]


class TestLongMemEvalRouting:
    def test_dry_run_validates_dataset_shape(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(_make_minimal_longmemeval_dataset(), f)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "-m", "benchmarks.external.longmemeval.run",
                 "--dataset-path", tmp_path, "--dry-run"],
                capture_output=True, text=True, timeout=30,
            )
            report = json.loads(result.stdout)
            assert report["mode"] == "dry-run"
            assert report["case_count"] == 3
            assert "information_extraction" in report["categories"]
            assert "knowledge_updates" in report["categories"]
            assert isinstance(report["fixture_hash"], str)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_missing_dataset_errors_cleanly(self):
        result = subprocess.run(
            [sys.executable, "-m", "benchmarks.external.longmemeval.run",
             "--dataset-path", "/nonexistent/longmemeval.json", "--dry-run"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode != 0

    def test_expected_500_questions_warning(self):
        """Report issues when case count != 500."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(_make_minimal_longmemeval_dataset(), f)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "-m", "benchmarks.external.longmemeval.run",
                 "--dataset-path", tmp_path, "--dry-run"],
                capture_output=True, text=True, timeout=30,
            )
            report = json.loads(result.stdout)
            assert report["case_count"] == 3
            assert report["valid"] is False  # not 500 questions
            assert len(report["validation_issues"]) > 0
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_missing_categories_reported(self):
        """Missing expected categories are listed."""
        dataset = [{
            "sample_id": "lme-single",
            "conversation": [{"speaker": "user", "text": "Hello."}],
            "qa": [{"question": "What was said?", "answer": "Hello", "category": "information_extraction"}],
        }]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(dataset, f)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "-m", "benchmarks.external.longmemeval.run",
                 "--dataset-path", tmp_path, "--dry-run"],
                capture_output=True, text=True, timeout=30,
            )
            report = json.loads(result.stdout)
            assert len(report["missing_categories"]) >= 4
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_seam_cli_routes_longmemeval_dataset_dry_run(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(_make_minimal_longmemeval_dataset(), f)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "seam", "bench", "external", "longmemeval",
                    "--dataset-path", tmp_path, "--dry-run", "--format", "json",
                ],
                capture_output=True, text=True, timeout=30,
            )
            assert result.returncode != 2, result.stderr
            report = json.loads(result.stdout)
            assert report["mode"] == "dry-run"
            assert report["case_count"] == 3
            assert report["valid"] is False
        finally:
            Path(tmp_path).unlink(missing_ok=True)
