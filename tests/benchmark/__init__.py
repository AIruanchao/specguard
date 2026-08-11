"""
Multi-model vote benchmark package.

Provides a frozen ground-truth dataset of 10 SDD (Spec-Driven Development)
proposal review samples, a blind-protocol harness that hides the ground
truth from the model under test, and a single-vs-ensemble accuracy
comparison framework.

The package never imports the production voting script
(~/.hermes/scripts/multi_model_vote.py) at import time; it instead
defines its own pluggable model-client interface so tests are hermetic
and deterministic by default. Real NewAPI calls can be opted into via
the SPECGUARD_BENCHMARK_REAL=1 env var; see baseline_comparison.py.
"""
from .vote_benchmark import (
    BenchmarkSample,
    BENCHMARK_SAMPLES,
    PROPOSAL_BODY_BY_ID,
    score_within_range,
    verdict_from_score,
    expected_verdict,
    expected_score_range,
)

__all__ = [
    "BenchmarkSample",
    "BENCHMARK_SAMPLES",
    "PROPOSAL_BODY_BY_ID",
    "score_within_range",
    "verdict_from_score",
    "expected_verdict",
    "expected_score_range",
]
