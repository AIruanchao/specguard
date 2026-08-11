"""Spec <-> Test traceability matrix tests.

A traceability matrix links each spec requirement to one or more test cases
that prove it. SDD treats every spec as untested until it has at least one
mapping, and missing mappings are surfaced as WARN (not silent).

Contract under test:
  * Each spec must have at least one requirement->test mapping.
  * A missing mapping produces a WARN entry (severity="warn"), not a hard error.
  * The matrix is "complete" when every spec has at least one mapping.
  * Reverse lookup (test -> requirements) must also work.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Traceability data model (test-local).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RequirementMapping:
    """A single link from a spec requirement to a test that covers it."""
    spec_id: str
    requirement_id: str
    test_id: str


@dataclass
class TraceabilityMatrix:
    """In-memory store of requirement <-> test mappings with health checks."""

    mappings: list[RequirementMapping] = field(default_factory=list)

    # --- queries ---

    def tests_for(self, spec_id: str) -> list[str]:
        """Return the list of test_ids that cover requirements in ``spec_id``."""
        seen: list[str] = []
        for mapping in self.mappings:
            if mapping.spec_id == spec_id and mapping.test_id not in seen:
                seen.append(mapping.test_id)
        return seen

    def requirements_for(self, test_id: str) -> list[str]:
        """Return the list of requirement_ids that ``test_id`` covers."""
        seen: list[str] = []
        for mapping in self.mappings:
            if mapping.test_id == test_id and mapping.requirement_id not in seen:
                seen.append(mapping.requirement_id)
        return seen

    def specs(self) -> list[str]:
        """Return the unique list of spec_ids referenced in the matrix."""
        return sorted({mapping.spec_id for mapping in self.mappings})

    # --- health checks ---

    def missing_mappings(self, known_spec_ids: list[str]) -> list[str]:
        """Return the subset of ``known_spec_ids`` that have no test coverage."""
        covered = set(self.specs())
        return [spec for spec in known_spec_ids if spec not in covered]

    def warnings(self, known_spec_ids: list[str]) -> list[dict]:
        """Return WARN entries for every spec without a mapping."""
        return [
            {
                "severity": "warn",
                "spec_id": spec_id,
                "message": (
                    f"Spec {spec_id!r} has no test mapping; "
                    "every spec must have at least 1 requirement->test link."
                ),
            }
            for spec_id in self.missing_mappings(known_spec_ids)
        ]

    def is_complete(self, known_spec_ids: list[str]) -> bool:
        """Return True when every known spec has at least one test mapping."""
        return len(self.missing_mappings(known_spec_ids)) == 0


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _fixture_matrix() -> TraceabilityMatrix:
    """Return a representative matrix used across the test class."""
    return TraceabilityMatrix(
        mappings=[
            RequirementMapping("SPEC-SE-001", "REQ-SE-1", "test_seal_position"),
            RequirementMapping("SPEC-SE-001", "REQ-SE-2", "test_seal_opacity"),
            RequirementMapping("SPEC-PR-002", "REQ-PR-1", "test_pdf_render"),
            RequirementMapping("SPEC-AU-003", "REQ-AU-1", "test_auth_token"),
        ]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTraceabilityMatrix:
    """Validate requirement <-> test mapping structure and health checks."""

    def test_each_spec_has_at_least_one_test(self):
        """Every spec_id in the matrix must map to at least one test_id."""
        matrix = _fixture_matrix()

        for spec_id in matrix.specs():
            assert len(matrix.tests_for(spec_id)) >= 1, (
                f"Spec {spec_id} must have at least 1 test mapping"
            )

    def test_tests_for_returns_covered_tests(self):
        """tests_for(spec_id) returns the set of test_ids for that spec."""
        matrix = _fixture_matrix()

        assert sorted(matrix.tests_for("SPEC-SE-001")) == [
            "test_seal_opacity",
            "test_seal_position",
        ]
        assert matrix.tests_for("SPEC-PR-002") == ["test_pdf_render"]
        assert matrix.tests_for("SPEC-NOPE-999") == []

    def test_requirements_for_returns_test_reach(self):
        """requirements_for(test_id) returns the requirement_ids the test covers."""
        matrix = _fixture_matrix()

        assert matrix.requirements_for("test_seal_position") == ["REQ-SE-1"]
        assert matrix.requirements_for("test_seal_opacity") == ["REQ-SE-2"]
        assert matrix.requirements_for("test_unrelated") == []

    def test_missing_mapping_emits_warn(self):
        """A known spec without any mapping must be reported as a WARN."""
        matrix = TraceabilityMatrix(
            mappings=[
                RequirementMapping("SPEC-A", "REQ-A-1", "test_a"),
            ]
        )

        warnings = matrix.warnings(["SPEC-A", "SPEC-B"])
        severities = {entry["severity"] for entry in warnings}
        spec_ids = {entry["spec_id"] for entry in warnings}

        # Only SPEC-B is missing; the warning severity must be "warn".
        assert "warn" in severities
        assert spec_ids == {"SPEC-B"}
        assert all(entry["severity"] == "warn" for entry in warnings)

    def test_complete_matrix_has_no_warnings(self):
        """When every known spec is covered, no warnings are emitted."""
        matrix = _fixture_matrix()

        warnings = matrix.warnings(["SPEC-SE-001", "SPEC-PR-002", "SPEC-AU-003"])

        assert warnings == []
        assert matrix.is_complete(["SPEC-SE-001", "SPEC-PR-002", "SPEC-AU-003"]) is True

    def test_incomplete_matrix_reports_gaps(self):
        """An incomplete matrix is_complete() must be False and enumerate gaps."""
        matrix = _fixture_matrix()

        gaps = matrix.missing_mappings(
            ["SPEC-SE-001", "SPEC-PR-002", "SPEC-AU-003", "SPEC-X-999"]
        )

        assert gaps == ["SPEC-X-999"]
        assert matrix.is_complete(
            ["SPEC-SE-001", "SPEC-PR-002", "SPEC-AU-003", "SPEC-X-999"]
        ) is False

    def test_duplicate_mappings_are_collapsed_in_queries(self):
        """Duplicate (spec, requirement, test) triples must not inflate the result."""
        matrix = TraceabilityMatrix(
            mappings=[
                RequirementMapping("SPEC-A", "REQ-A-1", "test_a"),
                RequirementMapping("SPEC-A", "REQ-A-1", "test_a"),  # dup
                RequirementMapping("SPEC-A", "REQ-A-1", "test_b"),  # new test
            ]
        )

        # tests_for must return unique test_ids only.
        assert sorted(matrix.tests_for("SPEC-A")) == ["test_a", "test_b"]
        # The same requirement listed twice must not double-count in reverse lookup.
        assert matrix.requirements_for("test_a") == ["REQ-A-1"]

    def test_empty_matrix_is_safe(self):
        """An empty matrix reports every known spec as missing (no crash)."""
        matrix = TraceabilityMatrix()

        assert matrix.specs() == []
        assert matrix.tests_for("anything") == []
        assert matrix.missing_mappings(["SPEC-A", "SPEC-B"]) == ["SPEC-A", "SPEC-B"]
        assert matrix.is_complete([]) is True
        assert matrix.warnings([]) == []
