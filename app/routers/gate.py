"""门禁引擎路由 — 包装gate_engine.py核心逻辑"""
import os, json, re, sys
from pathlib import Path
from fastapi import APIRouter
from app.models import GateCheckRequest, GateCheckResponse
from app.config import DATA_DIR

router = APIRouter()

# 加载module_paths.json
_MODULE_PATHS_FILE = DATA_DIR / "module_paths.json"


def _load_module_paths():
    """加载模块→文件映射"""
    # 查找module_paths.json（app/data/或项目sdd/scripts/）
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
    """从目标项目加载module_paths.json"""
    p = Path(project_path) / "sdd" / "scripts" / "module_paths.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return _load_module_paths()


def _identify_affected_modules(changed_files, module_paths):
    """识别受影响的模块"""
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
    """从PR描述中提取Spec引用"""
    if not pr_body:
        return []
    pattern = r'sdd/(?:domain-spec|change-log|enterprise-spec)/[^\s\)\]"\'<>]+\.md'
    return list(set(re.findall(pattern, pr_body)))


@router.post("/check", response_model=GateCheckResponse)
async def check_gate(req: GateCheckRequest):
    """检查PR是否满足SDD门禁要求"""
    # 加载模块映射
    module_paths = _load_module_paths_for_project(req.project_path)

    # 识别受影响模块
    affected_modules, unmatched = _identify_affected_modules(
        req.changed_files, module_paths
    )

    # 检查hotfix/豁免标签
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

    # 未匹配的受保护文件
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

    # 提取Spec引用
    spec_refs = _extract_spec_refs(req.pr_body)

    if not spec_refs:
        return GateCheckResponse(
            passed=False,
            affected_modules=sorted(affected_modules),
            errors=["业务代码变更未引用任何sdd/Spec文件"],
        )

    # 验证Spec文件存在性
    project_root = Path(req.project_path)
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
