"""
Vote Benchmark — Frozen evaluation set for multi-model voting system.

10 SDD proposal samples with known correct scores and verdicts.
Used to measure voting precision vs single-model baseline.
"""

# Frozen benchmark: 10 SDD proposal evaluation samples
# Each sample has: title, summary, expected_score_range (low, high), expected_verdict
BENCHMARK_SAMPLES = [
    {
        "title": "Well-designed CI pipeline",
        "summary": "7-stage CI with lint, test, coverage gate, build, security scan. Branch protection required checks. All 7 systems covered.",
        "expected_score_range": (30, 35),
        "expected_verdict": "APPROVE",
    },
    {
        "title": "Basic CI without coverage gate",
        "summary": "CI runs tests but no coverage threshold. Missing security scan. 3/7 systems only.",
        "expected_score_range": (20, 26),
        "expected_verdict": "CONCERNS",
    },
    {
        "title": "CI exists but no branch protection",
        "summary": "GitHub Actions configured but merge not blocked on failure. Can bypass via admin.",
        "expected_score_range": (15, 20),
        "expected_verdict": "CONCERNS",
    },
    {
        "title": "No CI at all",
        "summary": "Direct push to main. No tests, no lint, no coverage. Vibe coding.",
        "expected_score_range": (7, 12),
        "expected_verdict": "BLOCK",
    },
    {
        "title": "Coverage 45% with auto-improve cron",
        "summary": "Current coverage below 60% target. Daily cron auto-generates tests. Expected to reach 80% in 14 days.",
        "expected_score_range": (22, 28),
        "expected_verdict": "CONCERNS",
    },
    {
        "title": "AI repair 19% success rate",
        "summary": "Only 6/31 repairs succeeded. Root cause bug fixed. Need 100 samples to prove >50%.",
        "expected_score_range": (12, 18),
        "expected_verdict": "BLOCK",
    },
    {
        "title": "Multi-model voting 17 rounds",
        "summary": "4-model voting ran 17 rounds. Corrected self-assessment inflation. But no frozen benchmark or blind test.",
        "expected_score_range": (22, 27),
        "expected_verdict": "CONCERNS",
    },
    {
        "title": "Complete SDD with verified gates",
        "summary": "All 7 systems have spec, tests, CI, coverage >=60%, branch protection. Zero-debt gate blocks merge. Verified end-to-end.",
        "expected_score_range": (30, 35),
        "expected_verdict": "APPROVE",
    },
    {
        "title": "Spec draft not confirmed",
        "summary": "Spec files exist but status=draft. No human review. No test mapping. No traceability.",
        "expected_score_range": (14, 19),
        "expected_verdict": "BLOCK",
    },
    {
        "title": "Reverse engine 83% regex accuracy",
        "summary": "Python AST solid. TypeScript regex 83% on spike. No frozen dataset. No P/R/F1 metrics. No layered report.",
        "expected_score_range": (18, 24),
        "expected_verdict": "CONCERNS",
    },
]


def test_benchmark_samples_exist():
    """Test that benchmark samples are defined."""
    assert len(BENCHMARK_SAMPLES) >= 10, f"Expected >=10 samples, got {len(BENCHMARK_SAMPLES)}"


def test_benchmark_samples_structure():
    """Test that each benchmark sample has required fields."""
    for i, sample in enumerate(BENCHMARK_SAMPLES):
        assert "title" in sample, f"Sample {i} missing title"
        assert "expected_score_range" in sample, f"Sample {i} missing expected_score_range"
        assert "expected_verdict" in sample, f"Sample {i} missing expected_verdict"


def test_benchmark_score_ranges_valid():
    """Test that score ranges are valid (low <= high, within 7-35)."""
    for i, sample in enumerate(BENCHMARK_SAMPLES):
        low, high = sample.get("expected_score_range", (0, 0))
        assert 7 <= low <= 35, f"Sample {i} low={low} out of range"
        assert 7 <= high <= 35, f"Sample {i} high={high} out of range"
        assert low <= high, f"Sample {i} low({low}) > high({high})"


def test_benchmark_verdicts_valid():
    """Test that verdicts are valid values."""
    valid_verdicts = {"APPROVE", "CONCERNS", "BLOCK"}
    for i, sample in enumerate(BENCHMARK_SAMPLES):
        verdict = sample.get("expected_verdict", "")
        assert verdict in valid_verdicts, f"Sample {i} verdict={verdict} not in {valid_verdicts}"


def test_benchmark_midpoint_consistency():
    """Test that the midpoint of each score band is consistent with its verdict."""
    for i, sample in enumerate(BENCHMARK_SAMPLES):
        low, high = sample["expected_score_range"]
        midpoint = (low + high) / 2
        verdict = sample["expected_verdict"]
        if verdict == "APPROVE":
            assert midpoint >= 28, f"Sample {i} APPROVE but midpoint={midpoint} < 28"
        elif verdict == "BLOCK":
            assert midpoint < 18, f"Sample {i} BLOCK but midpoint={midpoint} >= 18"
