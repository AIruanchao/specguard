"""
test_vote_benchmark.py — Frozen ground-truth dataset for multi-model voting.

10 SDD proposal samples with known correct scores and verdicts.
"""

BENCHMARK_SAMPLES = [
    {"title": "Well-designed CI pipeline", "summary": "7-stage CI with lint, test, coverage gate, build, security scan. Branch protection. 7 systems.", "expected_score_range": (30, 35), "expected_verdict": "APPROVE"},
    {"title": "Basic CI without coverage gate", "summary": "CI runs tests but no coverage threshold. Missing security scan. 3/7 systems only.", "expected_score_range": (20, 26), "expected_verdict": "CONCERNS"},
    {"title": "CI exists but no branch protection", "summary": "GitHub Actions configured but merge not blocked on failure.", "expected_score_range": (15, 20), "expected_verdict": "CONCERNS"},
    {"title": "No CI at all", "summary": "Direct push to main. No tests, no lint.", "expected_score_range": (7, 12), "expected_verdict": "BLOCK"},
    {"title": "Coverage 45% with auto-improve cron", "summary": "Below 60% target. Daily cron auto-generates tests. Expected 80% in 14 days.", "expected_score_range": (22, 28), "expected_verdict": "CONCERNS"},
    {"title": "AI repair 19% success rate", "summary": "Only 6/31 repairs succeeded. Root cause fixed. Need 100 samples.", "expected_score_range": (12, 18), "expected_verdict": "BLOCK"},
    {"title": "Multi-model voting 17 rounds", "summary": "4-model voting ran 17 rounds. Corrected self-assessment. No frozen benchmark yet.", "expected_score_range": (22, 27), "expected_verdict": "CONCERNS"},
    {"title": "Complete SDD with verified gates", "summary": "All 7 systems have spec, tests, CI, coverage>=60%, branch protection. Zero-debt gate.", "expected_score_range": (30, 35), "expected_verdict": "APPROVE"},
    {"title": "Spec draft not confirmed", "summary": "Spec files exist but status=draft. No human review. No test mapping.", "expected_score_range": (14, 19), "expected_verdict": "BLOCK"},
    {"title": "Reverse engine 83% regex accuracy", "summary": "Python AST solid. TS regex 83% on spike. No frozen dataset.", "expected_score_range": (18, 24), "expected_verdict": "CONCERNS"},
]


def test_benchmark_samples_exist():
    """Test that benchmark samples are defined."""
    assert len(BENCHMARK_SAMPLES) >= 10


def test_benchmark_samples_structure():
    """Test that each benchmark sample has required fields."""
    for i, sample in enumerate(BENCHMARK_SAMPLES):
        assert "title" in sample, f"Sample {i} missing title"
        assert "expected_score_range" in sample
        assert "expected_verdict" in sample


def test_benchmark_score_ranges_valid():
    """Test that score ranges are valid."""
    for i, sample in enumerate(BENCHMARK_SAMPLES):
        low, high = sample.get("expected_score_range", (0, 0))
        assert 7 <= low <= 35
        assert 7 <= high <= 35
        assert low <= high


def test_benchmark_verdicts_valid():
    """Test that verdicts are valid."""
    valid = {"APPROVE", "CONCERNS", "BLOCK"}
    for i, sample in enumerate(BENCHMARK_SAMPLES):
        assert sample.get("expected_verdict", "") in valid


def test_benchmark_midpoint_consistency():
    """Test midpoint-verdict consistency."""
    for i, sample in enumerate(BENCHMARK_SAMPLES):
        low, high = sample["expected_score_range"]
        mid = (low + high) / 2
        v = sample["expected_verdict"]
        if v == "APPROVE":
            assert mid >= 28
        elif v == "BLOCK":
            assert mid < 18


from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class BenchmarkSample:
    """A frozen benchmark sample for voting evaluation."""
    sample_id: str
    title: str
    summary: str
    expected_score_range: Tuple[int, int]
    expected_verdict: str
    proposal_body: str = ""

    @property
    def midpoint(self) -> float:
        return sum(self.expected_score_range) / 2


# Build typed samples from BENCHMARK_SAMPLES
TYPED_SAMPLES: List[BenchmarkSample] = [
    BenchmarkSample(
        sample_id=f"S{i+1:02d}",
        title=s["title"],
        summary=s["summary"],
        expected_score_range=s["expected_score_range"],
        expected_verdict=s["expected_verdict"],
        proposal_body=s["summary"],
    )
    for i, s in enumerate(BENCHMARK_SAMPLES)
]

# Export under the names delegation code expects
PROPOSAL_BODY_BY_ID: Dict[str, str] = {s.sample_id: s.proposal_body for s in TYPED_SAMPLES}


def expected_score_range(sample_id: str) -> Tuple[int, int]:
    """Get expected score range for a sample."""
    for s in TYPED_SAMPLES:
        if s.sample_id == sample_id:
            return s.expected_score_range
    raise KeyError(f"Unknown sample_id: {sample_id}")


def expected_verdict(sample_id: str) -> str:
    """Get expected verdict for a sample."""
    for s in TYPED_SAMPLES:
        if s.sample_id == sample_id:
            return s.expected_verdict
    raise KeyError(f"Unknown sample_id: {sample_id}")


def score_within_range(score: float, sample_id: str) -> bool:
    """Check if a score falls within the expected range."""
    low, high = expected_score_range(sample_id)
    return low <= score <= high


def verdict_from_score(score: float) -> str:
    """Derive verdict from a score using fixed thresholds."""
    if score >= 28:
        return "APPROVE"
    elif score < 18:
        return "BLOCK"
    else:
        return "CONCERNS"


# Alias for delegation compatibility: some code uses .id instead of .sample_id
# Add id property to BenchmarkSample
def _benchmark_id(self):
    return self.sample_id
BenchmarkSample.id = property(_benchmark_id)
