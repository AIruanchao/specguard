"""Gate engine routes wrapping gate_engine.py core logic."""
import json, re
from pathlib import Path
from fastapi import APIRouter
from app.models import GateCheckRequest, GateCheckResponse
from app.config import DATA_DIR, resolve_project_path

router = APIRouter()

# Load module_paths.json.
_MODULE_PATHS_FILE = DATA_DIR / "module_paths.json"


def _load_module_paths():
    """Load the module-to-file mapping."""
    # Search app/data first, then the legacy project data path.
    candidates = [
        _MODULE_PATHS_FILE,
        Path(__file__).resolve().parent.parent / "data" / "module_paths.json",
    ]
    for p in candidates:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return {}


def _load_module_paths_for_project(project_path: str):
    """Load module_paths.json from the target project first."""
    p = Path(project_path) / "sdd" / "scripts" / "module_paths.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return _load_module_paths()


def _identify_affected_modules(changed_files, module_paths):
    """Identify modules affected by changed files."""
    file_to_module = {}
    for module, files in module_paths.items():
        for f in files:
            file_to_module[f] = module

    affected = set()
    unmatched = []
    for f in changed_files:
        if f in file_to_module:
            affected.add(file_to_module[f])
        elif "contracts/" in f:
            affected.add("document-state-machine")
        else:
            unmatched.append(f)
    return affected, unmatched


def _extract_spec_refs(pr_body):
    """Extract Spec references from a PR body."""
    if not pr_body:
        return []
    pattern = r'sdd/(?:domain-spec|change-log|enterprise-spec)/[^\s\)\]"\'<>]+\.md'
    return list(set(re.findall(pattern, pr_body)))


@router.post("/check", response_model=GateCheckResponse)
async def check_gate(req: GateCheckRequest):
    """Check whether a PR satisfies the SDD gate."""
    project_root = resolve_project_path(req.project, req.project_path)

    # Load module mappings.
    module_paths = _load_module_paths_for_project(str(project_root))

    # Identify affected modules.
    affected_modules, unmatched = _identify_affected_modules(
        req.changed_files, module_paths
    )

    # Check hotfix and exemption labels.
    if "hotfix-emergency" in req.pr_labels:
        return GateCheckResponse(
            passed=True,
            affected_modules=sorted(affected_modules),
            warnings=["hotfix-emergency标签豁免（72小时内补Spec）"],
        )
    if "docs-only" in req.pr_labels or "dependency-bump" in req.pr_labels:
        return GateCheckResponse(
            passed=True,
            affected_modules=sorted(affected_modules),
            warnings=["docs-only/dependency-bump标签豁免"],
        )

    # Block unmatched protected files.
    protected_prefixes = ("app/routes/", "app/services/", "app/models.py", "app/schema.py", "app/auth.py")
    unmatched_protected = [f for f in unmatched if any(f.startswith(p) for p in protected_prefixes)]
    if unmatched_protected:
        return GateCheckResponse(
            passed=False,
            affected_modules=sorted(affected_modules),
            errors=[f"受保护路径下未匹配文件: {unmatched_protected}，请更新module_paths.json"],
        )

    if not affected_modules:
        return GateCheckResponse(passed=True, affected_modules=[])

    # Extract Spec references.
    spec_refs = _extract_spec_refs(req.pr_body)

    if not spec_refs:
        return GateCheckResponse(
            passed=False,
            affected_modules=sorted(affected_modules),
            errors=["业务代码变更未引用任何sdd/Spec文件"],
        )

    # Validate referenced Spec files exist.
    missing = []
    for ref in spec_refs:
        if not (project_root / ref).exists():
            missing.append(ref)

    if missing:
        return GateCheckResponse(
            passed=False,
            affected_modules=sorted(affected_modules),
            spec_refs=spec_refs,
            errors=[f"Spec文件不存在: {missing}"],
        )

    return GateCheckResponse(
        passed=True,
        affected_modules=sorted(affected_modules),
        spec_refs=spec_refs,
    )
