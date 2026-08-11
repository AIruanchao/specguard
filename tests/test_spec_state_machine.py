"""Spec state machine tests.

Validates the SDD spec lifecycle: draft -> review -> approved -> verified.

Contract under test:
  * Legal forward transitions: draft->review, review->approved, approved->verified.
  * Legal reverts: review->draft, approved->review.
  * Any other transition is illegal and must be blocked.
  * draft cannot pass the gate (status=invalid).
  * Only verified status counts toward the project completion rate.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Minimal state machine (test-local; mirrors the lifecycle used by gate.py
# and reverse_engine.generate_spec where status starts at "draft").
# ---------------------------------------------------------------------------

LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"review"},
    "review": {"approved", "draft"},
    "approved": {"verified", "review"},
    "verified": {"approved"},
}

COMPLETION_STATUSES: set[str] = {"verified"}

GATE_PASSING_STATUSES: set[str] = {"approved", "verified"}


class IllegalTransitionError(ValueError):
    """Raised when an attempt is made to move between incompatible states."""


def transition(current: str, target: str) -> str:
    """Move a spec from ``current`` to ``target`` or raise IllegalTransitionError."""
    if target not in LEGAL_TRANSITIONS.get(current, set()):
        raise IllegalTransitionError(
            f"Illegal spec transition: {current!r} -> {target!r}. "
            f"Allowed from {current!r}: {sorted(LEGAL_TRANSITIONS.get(current, set()))}"
        )
    return target


def can_pass_gate(status: str) -> bool:
    """Return True only when the spec is in a gate-passing state."""
    return status in GATE_PASSING_STATUSES


def counts_for_completion(status: str) -> bool:
    """Return True only when the spec is in a terminal-verified state."""
    return status in COMPLETION_STATUSES


def completion_rate(statuses: list[str]) -> float:
    """Compute the project completion rate as verified / total."""
    if not statuses:
        return 0.0
    verified = sum(1 for status in statuses if counts_for_completion(status))
    return verified / len(statuses)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSpecStateMachine:
    """Validate the draft -> review -> approved -> verified state machine."""

    def test_draft_to_review_is_legal(self):
        """Forward transition from draft to review must be allowed."""
        assert "draft" in LEGAL_TRANSITIONS
        assert "review" in LEGAL_TRANSITIONS["draft"]
        assert transition("draft", "review") == "review"

    def test_review_to_approved_is_legal(self):
        """Forward transition from review to approved must be allowed."""
        assert transition("review", "approved") == "approved"

    def test_approved_to_verified_is_legal(self):
        """Forward transition from approved to verified must be allowed."""
        assert transition("approved", "verified") == "verified"

    def test_legal_reverts_are_allowed(self):
        """Reverts review->draft and approved->review must be allowed."""
        assert transition("review", "draft") == "draft"
        assert transition("approved", "review") == "review"

    def test_draft_to_approved_is_blocked(self):
        """Skipping review (draft -> approved) must be illegal."""
        with pytest.raises(IllegalTransitionError):
            transition("draft", "approved")

    def test_draft_to_verified_is_blocked(self):
        """Skipping the full pipeline (draft -> verified) must be illegal."""
        with pytest.raises(IllegalTransitionError):
            transition("draft", "verified")

    def test_review_to_verified_is_blocked(self):
        """Skipping approved (review -> verified) must be illegal."""
        with pytest.raises(IllegalTransitionError):
            transition("review", "verified")

    def test_approved_to_draft_is_blocked(self):
        """No jumping backward past review (approved -> draft) must be illegal."""
        with pytest.raises(IllegalTransitionError):
            transition("approved", "draft")

    def test_draft_cannot_pass_gate(self):
        """A spec in draft must NOT be allowed to pass the gate."""
        # Only approved/verified may pass; draft must be blocked.
        assert can_pass_gate("draft") is False
        assert can_pass_gate("review") is False
        assert can_pass_gate("approved") is True
        assert can_pass_gate("verified") is True

    def test_only_verified_counts_for_completion(self):
        """Completion rate is computed from the verified status only."""
        statuses = ["draft", "review", "approved", "verified", "verified"]
        # 2 out of 5 are verified -> 0.4
        assert completion_rate(statuses) == pytest.approx(0.4)

        # Empty input is a safe zero, not a division error.
        assert completion_rate([]) == 0.0

        # Sanity: other statuses do not count.
        for status in ("draft", "review", "approved"):
            assert counts_for_completion(status) is False
        assert counts_for_completion("verified") is True
