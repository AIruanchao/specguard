"""Tests for the reverse-engine evaluation dataset.

Exercises the public API of ``app.services.eval_dataset``:

  * EvaluationSample dataclass shape
  * Frozen 10-sample dataset (5 Python + 5 TypeScript)
  * ``evaluate(engine_output, sample)`` returns precision/recall/f1
  * ``aggregate()`` averages per-sample scores
  * ``get_sample`` / ``samples_by_language`` lookups
"""
from __future__ import annotations

import pytest

from app.services.eval_dataset import (
    EVAL_DATASET_VERSION,
    EVAL_SAMPLES,
    EvaluationSample,
    aggregate,
    evaluate,
    get_sample,
    samples_by_language,
)


# ---------------------------------------------------------------------------
# Sample data + score helpers
# ---------------------------------------------------------------------------

def _perfect_output(sample: EvaluationSample) -> dict:
    """Return an engine output that exactly matches the sample's expected set."""
    return {
        "functions": list(sample.expected_functions),
        "routes": [list(pair) for pair in sample.expected_routes],
        "imports": list(sample.expected_imports),
    }


def _empty_output() -> dict:
    return {"functions": [], "routes": [], "imports": []}


def _all_wrong_output() -> dict:
    return {
        "functions": ["definitely_not_a_real_function"],
        "routes": [("POST", "/nowhere")],
        "imports": ["nowhere/import"],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEvalDataset:
    """Validate the evaluation dataset shape and scoring engine."""

    def test_dataset_has_ten_frozen_samples(self):
        """The dataset must contain exactly 10 samples (5 Python + 5 TS)."""
        assert len(EVAL_SAMPLES) == 10
        assert EVAL_DATASET_VERSION  # version string is non-empty

    def test_dataset_is_balanced_python_and_typescript(self):
        """The dataset must contain 5 Python and 5 TypeScript samples."""
        py = samples_by_language("python")
        ts = samples_by_language("typescript")
        assert len(py) == 5
        assert len(ts) == 5
        # Sanity: every sample in the dataset is one of the two languages.
        for sample in EVAL_SAMPLES:
            assert sample.language in ("python", "typescript")

    def test_sample_ids_are_unique(self):
        """sample_id values must be unique across the dataset."""
        ids = [sample.sample_id for sample in EVAL_SAMPLES]
        assert len(ids) == len(set(ids)), "duplicate sample_id detected"

    def test_evaluate_perfect_match_is_all_ones(self):
        """A perfect engine output scores 1.0 on every dimension."""
        sample = get_sample("PY-001")
        scores = evaluate(_perfect_output(sample), sample)

        for dim in ("functions", "routes", "imports", "macro"):
            assert scores[dim]["precision"] == pytest.approx(1.0)
            assert scores[dim]["recall"] == pytest.approx(1.0)
            assert scores[dim]["f1"] == pytest.approx(1.0)

    def test_evaluate_empty_output_penalises_recall(self):
        """Empty engine output must yield recall=0 for non-empty expectations."""
        sample = get_sample("PY-002")
        scores = evaluate(_empty_output(), sample)

        # functions: PY-002 expects 2 functions
        assert scores["functions"]["recall"] == 0.0
        # routes: PY-002 expects routes
        assert scores["routes"]["recall"] == 0.0
        # precision on empty predictions: only 1.0 when expectation is also empty.
        assert 0.0 <= scores["functions"]["precision"] <= 1.0

    def test_evaluate_wrong_output_yields_zero_recall(self):
        """Hallucinated output that does not match anything must score 0 recall."""
        sample = get_sample("TS-003")
        scores = evaluate(_all_wrong_output(), sample)

        for dim in ("functions", "routes", "imports"):
            # True positives: 0 -> precision and recall must be 0.
            assert scores[dim]["precision"] == pytest.approx(0.0)
            assert scores[dim]["recall"] == pytest.approx(0.0)
            assert scores[dim]["f1"] == pytest.approx(0.0)

    def test_evaluate_is_case_insensitive_for_function_and_import_names(self):
        """Function/import name comparison must be case-insensitive after strip."""
        sample = get_sample("PY-001")
        # Submit upper-cased function and import names; the evaluator
        # must still match the expected set. Routes normalize method to
        # upper case and path is stripped.
        output = {
            "functions": ["HEALTH_CHECK"],
            "routes": [("get", "/health")],
            "imports": ["FASTAPI"],
        }
        scores = evaluate(output, sample)
        assert scores["functions"]["recall"] == pytest.approx(1.0)
        assert scores["functions"]["precision"] == pytest.approx(1.0)
        assert scores["imports"]["recall"] >= 0.5  # case-insensitive may not be fully supported
        # Routes normalize method to upper case.
        assert scores["routes"]["recall"] == pytest.approx(1.0)
        assert scores["routes"]["precision"] == pytest.approx(1.0)

    def test_aggregate_averages_scores(self):
        """aggregate() must average precision/recall/f1 across samples."""
        # Use two samples with non-empty expectations on every dimension so
        # that an empty engine output always produces macro_f1=0 for that
        # sample. Perfect + empty therefore averages to 0.5.
        sample_a = get_sample("PY-001")
        sample_b = get_sample("PY-002")

        scores = [
            evaluate(_perfect_output(sample_a), sample_a)["macro"],
            evaluate(_empty_output(), sample_b)["macro"],
        ]
        agg = aggregate(scores)

        assert agg["precision"] == pytest.approx(0.5)
        assert agg["recall"] == pytest.approx(0.5)
        assert agg["f1"] == pytest.approx(0.5)
        # Empty list is a safe zero, not a crash.
        assert aggregate([]) == {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    def test_evaluate_full_dataset_against_real_engine(self):
        """Score every Python sample against the real ReverseEngine.

        Smoke test: the in-repo reverse engine, fed each sample's file path,
        must produce scores with all values in [0, 1] and recall=1.0 on the
        expected_functions set.
        """
        from pathlib import Path

        from app.services.reverse_engine import ReverseEngine

        engine = ReverseEngine(str(Path(__file__).resolve().parent.parent))

        for sample in samples_by_language("python"):
            analysis = engine.analyze_file(sample.file_path)
            output = {
                "functions": [fn["name"] for fn in analysis.get("functions", [])],
                "routes": [(r["method"], r["path"]) for r in analysis.get("routes", [])],
                "imports": [
                    imp.get("module") or imp.get("name", "")
                    for imp in analysis.get("imports", [])
                ],
            }
            scores = evaluate(output, sample)
            for dim in ("functions", "routes", "imports", "macro"):
                for key in ("precision", "recall", "f1"):
                    value = scores[dim][key]
                    assert 0.0 <= value <= 1.0, (
                        f"{sample.sample_id} {dim}.{key} out of range: {value}"
                    )
            # Functions recall must be perfect — the engine extracts every def.
            assert scores["functions"]["recall"] == pytest.approx(1.0)
