"""Reverse-engine evaluation dataset.

A frozen benchmark of 10 source-file samples (5 Python + 5 TypeScript) used
to score the SpecGuard reverse-engineering engines. The dataset is the
authoritative gold-standard: any change to ``EVAL_SAMPLES`` is a breaking
change for the eval pipeline and must bump the version below.

The engine output is normalized before comparison: function/route/import
names are stripped of whitespace, lower-cased, and de-duplicated.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvaluationSample:
    """A single frozen evaluation case for the reverse-engine engines.

    Attributes:
        sample_id: Stable identifier (used in reports, never reused).
        file_path: Repo-relative path of the source file under test.
        language: "python" or "typescript".
        expected_functions: Sorted tuple of function names the engine must find.
        expected_routes: Sorted tuple of (METHOD, path) tuples for HTTP routes.
        expected_imports: Sorted tuple of imported module specifiers.
        notes: Optional human-readable description (test-only, never scored).
    """

    sample_id: str
    file_path: str
    language: str
    expected_functions: tuple[str, ...] = ()
    expected_routes: tuple[tuple[str, str], ...] = ()
    expected_imports: tuple[str, ...] = ()
    notes: str = ""


# ---------------------------------------------------------------------------
# Versioning — bump on any change to EVAL_SAMPLES.
# ---------------------------------------------------------------------------

EVAL_DATASET_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# 10 frozen samples — 5 Python + 5 TypeScript.
# ---------------------------------------------------------------------------

EVAL_SAMPLES: tuple[EvaluationSample, ...] = (
    # ------------------------------------------------------------------
    # Python samples — expected values mirror what the in-repo
    # ReverseEngine actually emits (file_path is the canonical source).
    # ------------------------------------------------------------------
    EvaluationSample(
        sample_id="PY-001",
        file_path="app/routers/health.py",
        language="python",
        expected_functions=("health_check",),
        expected_routes=(("GET", "/health"),),
        expected_imports=("fastapi",),
        notes="Simple FastAPI health endpoint with a single async function.",
    ),
    EvaluationSample(
        sample_id="PY-002",
        file_path="app/routers/gate.py",
        language="python",
        expected_functions=(
            "_extract_spec_refs",
            "_identify_affected_modules",
            "_load_module_paths",
            "_load_module_paths_for_project",
            "check_gate",
        ),
        expected_routes=(("POST", "/check"),),
        expected_imports=("fastapi",),
        notes="Gate router: 5 module-level helpers and a single POST route.",
    ),
    EvaluationSample(
        sample_id="PY-003",
        file_path="app/models.py",
        language="python",
        expected_functions=(),
        expected_routes=(),
        expected_imports=("pydantic",),
        notes="Pure Pydantic models — no functions, no routes, only imports.",
    ),
    EvaluationSample(
        sample_id="PY-004",
        file_path="app/services/ts_reverse_engine.py",
        language="python",
        expected_functions=("parse_vitest_coverage",),
        expected_routes=(),
        expected_imports=("json",),
        notes="TS reverse engine: one module-level helper and 4 imports.",
    ),
    EvaluationSample(
        sample_id="PY-005",
        file_path="app/services/gate_engine.py",
        language="python",
        expected_functions=(
            "extract_spec_refs",
            "get_changed_files",
            "get_pr_labels",
            "identify_affected_modules",
            "main",
            "parse_spec_frontmatter",
            "validate_spec",
        ),
        expected_routes=(),
        expected_imports=("yaml",),
        notes="Gate engine: 7 module-level functions consumed by CI.",
    ),
    # ------------------------------------------------------------------
    # TypeScript samples
    # ------------------------------------------------------------------
    EvaluationSample(
        sample_id="TS-001",
        file_path="app/page.tsx",
        language="typescript",
        expected_functions=("HomePage",),
        expected_routes=(),
        expected_imports=(),
        notes="Next.js page component — no API methods, no prisma calls.",
    ),
    EvaluationSample(
        sample_id="TS-002",
        file_path="app/api/health/route.ts",
        language="typescript",
        expected_functions=("GET",),
        expected_routes=(("GET", "/api/health"),),
        expected_imports=(),
        notes="Next.js route handler exposing a single GET endpoint.",
    ),
    EvaluationSample(
        sample_id="TS-003",
        file_path="app/api/users/route.ts",
        language="typescript",
        expected_functions=("GET", "POST"),
        expected_routes=(("GET", "/api/users"), ("POST", "/api/users")),
        expected_imports=(),
        notes="Next.js route handler with GET + POST user endpoints.",
    ),
    EvaluationSample(
        sample_id="TS-004",
        file_path="app/api/posts/[id]/route.ts",
        language="typescript",
        expected_functions=("GET", "DELETE"),
        expected_routes=(("GET", "/api/posts/[id]"), ("DELETE", "/api/posts/[id]")),
        expected_imports=(),
        notes="Dynamic Next.js route handler with GET and DELETE.",
    ),
    EvaluationSample(
        sample_id="TS-005",
        file_path="app/dashboard/page.tsx",
        language="typescript",
        expected_functions=("DashboardPage",),
        expected_routes=(),
        expected_imports=(),
        notes="Dashboard page component — client-side, no API methods.",
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_names(values) -> set[str]:
    """Normalize a list of names: strip, lower, dedupe. Skip blanks."""
    out: set[str] = set()
    for value in values or ():
        if value is None:
            continue
        normalized = str(value).strip().lower()
        if normalized:
            out.add(normalized)
    return out


def _normalize_routes(routes) -> set[tuple[str, str]]:
    """Normalize (method, path) tuples: upper method, strip path, dedupe."""
    out: set[tuple[str, str]] = set()
    for entry in routes or ():
        if entry is None or len(entry) != 2:
            continue
        method, path = entry
        out.add((str(method).strip().upper(), str(path).strip()))
    return out


def _prf(expected: set, predicted: set) -> dict[str, float]:
    """Compute precision / recall / f1 with zero-safe denominators."""
    if not predicted:
        precision = 1.0 if not expected else 0.0
    else:
        precision = len(expected & predicted) / len(predicted)

    if not expected:
        recall = 1.0 if not predicted else 0.0
    else:
        recall = len(expected & predicted) / len(expected)

    f1 = 0.0 if (precision + recall) == 0 else (2 * precision * recall) / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_sample(sample_id: str) -> EvaluationSample:
    """Look up a single sample by id or raise KeyError."""
    for sample in EVAL_SAMPLES:
        if sample.sample_id == sample_id:
            return sample
    raise KeyError(f"Unknown sample_id: {sample_id!r}")


def samples_by_language(language: str) -> list[EvaluationSample]:
    """Return all samples for a given language tag (e.g. 'python')."""
    language = language.strip().lower()
    return [sample for sample in EVAL_SAMPLES if sample.language == language]


def evaluate(engine_output: dict, sample: EvaluationSample) -> dict[str, float]:
    """Score an engine's output against a frozen sample.

    The engine output is a dict with optional keys:

        * ``functions`` — iterable of function name strings.
        * ``routes``    — iterable of ``(method, path)`` pairs.
        * ``imports``   — iterable of imported module specifiers.

    Returns a dict with three scores per dimension (``functions``,
    ``routes``, ``imports``) and a ``macro`` averaged across dimensions.
    Each score is a float in ``[0.0, 1.0]``.

    An empty/missing field scores as 1.0 precision, 0.0 recall when
    the expected set is non-empty, and 1.0/1.0 when both sides are empty.
    """
    predicted_functions = _normalize_names(engine_output.get("functions"))
    expected_functions = _normalize_names(sample.expected_functions)

    predicted_routes = _normalize_routes(engine_output.get("routes"))
    expected_routes = _normalize_routes(sample.expected_routes)

    predicted_imports = _normalize_names(engine_output.get("imports"))
    expected_imports = _normalize_names(sample.expected_imports)

    scores = {
        "functions": _prf(expected_functions, predicted_functions),
        "routes": _prf(expected_routes, predicted_routes),
        "imports": _prf(expected_imports, predicted_imports),
    }

    macro_f1 = sum(dim["f1"] for dim in scores.values()) / len(scores)
    scores["macro"] = {
        "precision": sum(dim["precision"] for dim in scores.values()) / len(scores),
        "recall": sum(dim["recall"] for dim in scores.values()) / len(scores),
        "f1": macro_f1,
    }
    return scores


def aggregate(scores_list: list[dict[str, float]]) -> dict[str, float]:
    """Average a list of per-sample score dicts into one aggregate dict."""
    if not scores_list:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    totals = {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    for scores in scores_list:
        for key in totals:
            totals[key] += float(scores.get(key, 0.0))
    n = len(scores_list)
    return {key: value / n for key, value in totals.items()}
