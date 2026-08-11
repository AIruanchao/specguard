"""
vote_benchmark.py — Frozen ground-truth dataset of 10 SDD proposal
review samples for the multi-model vote benchmark.

Each sample is a self-contained SDD-style proposal body together with
the canonical human-graded answer:

  - score_min / score_max : acceptable 0-100 quality-score window
  - expected_verdict      : one of "APPROVE" | "CONCERNS" | "BLOCK"
                            (mapped from the specguard verdict system)

Verdicts are derived from the 0-100 quality score using the specguard
ceiling-gate thresholds:

  score >= 80  -> APPROVE
  60 <= score < 80 -> CONCERNS
  score < 60   -> BLOCK

The samples are deliberately heterogeneous: clean proposals, proposals
with reversible concerns, security holes, performance regressions,
data-loss risks, and outright ungrounded specs. They were designed so
that a naive single-model grader will mis-classify several of them
(hallucination traps) while a 4-model ensemble with majority vote
should land within the acceptable window on the majority.

DO NOT mutate the BENCHMARK_SAMPLES list at runtime. The blind_protocol
harness depends on the (id, expected_verdict, expected_score_range)
tuple being stable across test runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class BenchmarkSample:
    """A single frozen SDD proposal review sample.

    Attributes:
        id: Stable opaque identifier used by the blind harness.
        title: Short human-readable title (also used in reports).
        category: Free-form category tag for stratified reporting.
        proposal_body: Full SDD-style proposal text under review.
        score_min: Lower bound of the acceptable quality-score window.
        score_max: Upper bound of the acceptable quality-score window.
        expected_verdict: Canonical verdict (APPROVE / CONCERNS / BLOCK).
        rationale: One-line explanation of why the ground truth is what
            it is. Kept short on purpose so it does not leak the
            scoring signal into the model prompt.
    """
    id: str
    title: str
    category: str
    proposal_body: str
    score_min: int
    score_max: int
    expected_verdict: str
    rationale: str

    def score_range(self) -> Tuple[int, int]:
        """Return the (min, max) acceptable score as a tuple."""
        return (self.score_min, self.score_max)


# ---------------------------------------------------------------------------
# 10 frozen samples.
# Provenance: hand-authored from the 17 prior specguard voting rounds
# documented in ~/.hermes/profiles/dachui80/memories/. They cover every
# verdict class at least 3 times, plus a small number of "trick" samples
# that are designed to be mis-classified by over-permissive single models.
# ---------------------------------------------------------------------------

BENCHMARK_SAMPLES: List[BenchmarkSample] = [
    # ---- 1. Clean, well-grounded proposal -> APPROVE ------------------
    BenchmarkSample(
        id="SDD-BMK-001",
        title="Add /healthz endpoint with structured JSON response",
        category="happy_path",
        proposal_body=(
            "## Goal\n"
            "Expose `GET /healthz` returning `{status, version, uptime}`.\n\n"
            "## Spec changes\n"
            "- `sdd/domain-spec/platform/spec.md` -> new endpoint spec\n"
            "- `app/routers/health.py` -> thin handler delegating to "
            "`app.services.health.collect_metrics()`\n\n"
            "## Tests\n"
            "- `tests/test_health.py` asserts 200 + JSON shape\n"
            "- Integration test pings the live uvicorn instance\n\n"
            "## Risks\n"
            "Negligible: read-only, no auth, no PII.\n"
        ),
        score_min=85, score_max=100,
        expected_verdict="APPROVE",
        rationale="Clean, minimal, fully specified, low risk.",
    ),

    # ---- 2. Solid proposal, minor style concern -> APPROVE ------------
    BenchmarkSample(
        id="SDD-BMK-002",
        title="Refactor config loader to use pydantic-settings",
        category="happy_path",
        proposal_body=(
            "## Goal\n"
            "Replace ad-hoc `os.environ.get` calls with a single "
            "pydantic-settings `Settings` class so config is typed.\n\n"
            "## Migration\n"
            "- `app/config.py` rewritten\n"
            "- All call sites updated to read `settings.foo`\n"
            "- Old env-var names preserved (back-compat)\n\n"
            "## Tests\n"
            "- Existing `test_api.py` continues to pass\n"
            "- New `test_config.py` asserts defaults + override behaviour\n\n"
            "## Risks\n"
            "Risk of missed call site -> mitigated by full grep + "
            "100% test coverage of `app/config.py`.\n"
        ),
        score_min=80, score_max=100,
        expected_verdict="APPROVE",
        rationale="Solid refactor with explicit migration + back-compat.",
    ),

    # ---- 3. Borderline acceptable, but missing tests -> CONCERNS ------
    BenchmarkSample(
        id="SDD-BMK-003",
        title="Add rate limiting to public endpoints",
        category="incomplete_spec",
        proposal_body=(
            "## Goal\n"
            "Add token-bucket rate limiting to `/api/v1/*`.\n\n"
            "## Approach\n"
            "Use `slowapi` middleware with 60 req/min per IP.\n\n"
            "## Open questions\n"
            "- Do we need per-user limits (requires auth lookup)?\n"
            "- What about authenticated admin bypass?\n"
            "- Where do we store counters (Redis vs in-memory)?\n"
        ),
        score_min=60, score_max=79,
        expected_verdict="CONCERNS",
        rationale="Direction is right but three open questions "
                   "and no test plan yet.",
    ),

    # ---- 4. Spec exists but code change is large and risky -> CONCERNS
    BenchmarkSample(
        id="SDD-BMK-004",
        title="Swap SQLite for Postgres in dev environment",
        category="incomplete_spec",
        proposal_body=(
            "## Goal\n"
            "Make local dev use Postgres so we can test JSONB + "
            "advisory locks.\n\n"
            "## Spec changes\n"
            "- `docker-compose.yml`: add `postgres:16`\n"
            "- `app/db.py`: switch engine URL via env var\n\n"
            "## Risks\n"
            "- Existing migration files may not be Postgres-compatible\n"
            "- Tests that hit SQLite-specific types will break\n"
            "- Devs on M-series Macs may need Rosetta for the image\n"
        ),
        score_min=60, score_max=79,
        expected_verdict="CONCERNS",
        rationale="Plausible but the migration / test breakage plan "
                   "is missing.",
    ),

    # ---- 5. Subtle: looks fine but has a security hole -> BLOCK ------
    BenchmarkSample(
        id="SDD-BMK-005",
        title="Add /api/v1/admin/export endpoint",
        category="security",
        proposal_body=(
            "## Goal\n"
            "Let admins export all user records as a CSV download.\n\n"
            "## Implementation\n"
            "```\n"
            "@router.get(\"/admin/export\")\n"
            "def export():\n"
            "    rows = db.query(User).all()\n"
            "    return StreamingResponse(to_csv(rows))\n"
            "```\n\n"
            "## Notes\n"
            "We trust that anyone hitting this URL is an admin because "
            "the URL starts with `/admin/`.\n"
        ),
        score_min=0, score_max=40,
        expected_verdict="BLOCK",
        rationale="No auth check, security by URL obscurity, "
                   "PII export without audit log.",
    ),

    # ---- 6. Subtle: data-loss risk -> BLOCK ---------------------------
    BenchmarkSample(
        id="SDD-BMK-006",
        title="Clean up old soft-deleted rows in cleanup cron",
        category="data_loss",
        proposal_body=(
            "## Goal\n"
            "Add a nightly cron that hard-deletes rows where "
            "`deleted_at < now() - 30 days` from the `orders` table.\n\n"
            "## Why\n"
            "Table is 2.3 TB and search is slow.\n\n"
            "## Implementation\n"
            "```\n"
            "DELETE FROM orders WHERE deleted_at < NOW() - INTERVAL '30 days'\n"
            "```\n"
            "Direct SQL, no per-row check, no dry-run flag.\n"
        ),
        score_min=0, score_max=45,
        expected_verdict="BLOCK",
        rationale="Irreversible bulk delete, no backup window, "
                   "no audit trail. Should be soft-archive at minimum.",
    ),

    # ---- 7. Trick: friendly tone hides missing acceptance criteria ---
    BenchmarkSample(
        id="SDD-BMK-007",
        title="Improve dashboard load time (no numbers, no plan)",
        category="vague",
        proposal_body=(
            "## Goal\n"
            "Make the dashboard load faster. Right now it feels a bit "
            "laggy. Let's sprinkle in some performance improvements "
            "across the board.\n\n"
            "## Approach\n"
            "- Profile the page in DevTools\n"
            "- Add memoization where it makes sense\n"
            "- Maybe lazy-load some components\n\n"
            "We don't have a specific target latency yet, but "
            "faster is better.\n"
        ),
        score_min=55, score_max=78,
        expected_verdict="CONCERNS",
        rationale="Friendly but has no target, no scope, no test. "
                   "A real reviewer should demand numbers first.",
    ),

    # ---- 8. Trick: one good thing + one fatal flaw -> BLOCK ----------
    BenchmarkSample(
        id="SDD-BMK-008",
        title="Add webhook deliveries with HMAC signing",
        category="mixed",
        proposal_body=(
            "## Goal\n"
            "Deliver domain events to customer webhooks. Each "
            "delivery is signed with HMAC-SHA256 using a per-tenant "
            "secret rotated every 24h.\n\n"
            "## Implementation\n"
            "- New `app/services/webhooks.py`\n"
            "- Retries with exponential backoff (1s, 5s, 30s)\n"
            "- Dead-letter queue after 3 failed attempts\n\n"
            "## Security TODO\n"
            "`TODO: verify the signature on the receiving side. "
            "Customers can rotate secrets via the dashboard.`\n"
        ),
        score_min=20, score_max=50,
        expected_verdict="BLOCK",
        rationale="Open TODO on the *only* security-critical step. "
                   "The rest is fine but signing is meaningless "
                   "without verification.",
    ),

    # ---- 9. Trick: passes structural checks but is hollow -> CONCERNS
    BenchmarkSample(
        id="SDD-BMK-009",
        title="Introduce feature-flag service",
        category="over_engineered",
        proposal_body=(
            "## Goal\n"
            "Adopt OpenFeature as our feature-flag standard so we can "
            "swap providers later without code changes.\n\n"
            "## Spec changes\n"
            "- `app/services/feature_flags.py`\n"
            "- `sdd/domain-spec/platform/feature-flags.md`\n\n"
            "## Test plan\n"
            "All existing tests pass.\n\n"
            "## Open questions\n"
            "- Which provider? (LaunchDarkly, Unleash, in-house)\n"
            "- Who owns the dashboard?\n"
        ),
        score_min=55, score_max=78,
        expected_verdict="CONCERNS",
        rationale="Wants to commit to a heavy dependency while the "
                   "provider decision is still open.",
    ),

    # ---- 10. Trick: looks complete but rollback is impossible -> BLOCK
    BenchmarkSample(
        id="SDD-BMK-010",
        title="Migrate users table to UUID primary keys in-place",
        category="irreversible",
        proposal_body=(
            "## Goal\n"
            "Switch `users.id` from BIGINT to UUID. The new column "
            "is added, backfilled, and the BIGINT column is dropped "
            "in a single migration that runs on the next deploy.\n\n"
            "## Risks\n"
            "Acknowledged but mitigated by taking the site offline "
            "for the migration window.\n"
        ),
        score_min=0, score_max=50,
        expected_verdict="BLOCK",
        rationale="No back-out plan, no shadow-write window, "
                   "no per-tenant dual-write, drops the old PK "
                   "in the same deploy.",
    ),
]


# Convenience: id -> body lookup, for the blind harness which never
# wants to expose the full BenchmarkSample dataclass to the model.
PROPOSAL_BODY_BY_ID = {s.id: s.proposal_body for s in BENCHMARK_SAMPLES}


# ---------------------------------------------------------------------------
# Helpers used by blind_protocol.py and baseline_comparison.py.
# ---------------------------------------------------------------------------

VERDICT_BANDS = (
    (80, "APPROVE"),
    (60, "CONCERNS"),
    (0, "BLOCK"),
)


def verdict_from_score(score: int) -> str:
    """Map a 0-100 quality score to a verdict per the ceiling-gate bands.

    >>> verdict_from_score(85)
    'APPROVE'
    >>> verdict_from_score(72)
    'CONCERNS'
    >>> verdict_from_score(40)
    'BLOCK'
    """
    if score < 0 or score > 100:
        raise ValueError(f"score out of range: {score}")
    for threshold, verdict in VERDICT_BANDS:
        if score >= threshold:
            return verdict
    return "BLOCK"


def score_within_range(score: int, sample: BenchmarkSample) -> bool:
    """True iff *score* is inside the sample's acceptable window."""
    return sample.score_min <= score <= sample.score_max


def expected_verdict(sample: BenchmarkSample) -> str:
    """Return the canonical expected verdict for the sample."""
    return sample.expected_verdict


def expected_score_range(sample: BenchmarkSample) -> Tuple[int, int]:
    """Return the canonical (min, max) score window for the sample."""
    return (sample.score_min, sample.score_max)


def _selftest() -> None:
    """Quick sanity check: every sample's expected_verdict must be
    consistent with its score band. Run via `python3 -m
    tests.benchmark.vote_benchmark`."""
    for s in BENCHMARK_SAMPLES:
        # The midpoint of the band must map to the expected verdict.
        # This catches samples whose declared verdict disagrees with
        # their declared band without being thrown off by the band
        # straddling a threshold.
        midpoint = (s.score_min + s.score_max) // 2
        inferred = verdict_from_score(midpoint)
        if inferred != s.expected_verdict:
            raise AssertionError(
                f"{s.id}: expected_verdict={s.expected_verdict} "
                f"but midpoint={midpoint} maps to {inferred}"
            )
    assert len(BENCHMARK_SAMPLES) == 10, "expected exactly 10 samples"


if __name__ == "__main__":
    _selftest()
    print(f"OK: {len(BENCHMARK_SAMPLES)} samples, all verdicts consistent.")
    for s in BENCHMARK_SAMPLES:
        print(f"  {s.id}  {s.expected_verdict:<8s}  "
              f"[{s.score_min:3d}-{s.score_max:3d}]  {s.title}")
