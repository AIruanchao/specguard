#!/usr/bin/env python3
"""
SDD Spec Gate — CI门禁脚本
依赖: dorny/paths-filter@v3 提供CHANGED_FILES (JSON列表)
依赖: PyYAML (GitHub Actions runner预装)

环境变量:
  CHANGED_FILES: JSON格式的变更文件列表 (由dorny/paths-filter提供)
  PR_BODY: PR描述
  PR_LABELS: JSON格式的PR标签列表
  GITHUB_WORKSPACE: 仓库根目录
"""
import sys, os, json, re
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML未安装: pip install pyyaml")
    sys.exit(2)

# ============================================================
# 加载模块映射（从module_paths.json，单一事实源）
# ============================================================
_SCRIPT_DIR = Path(__file__).parent
_MODULE_PATHS_FILE = _SCRIPT_DIR / "module_paths.json"

with open(_MODULE_PATHS_FILE) as f:
    MODULE_PATHS = json.load(f)

# 反向映射：文件 → 模块
FILE_TO_MODULE = {}
for module, files in MODULE_PATHS.items():
    for fpath in files:
        FILE_TO_MODULE[fpath] = module

# A级模块列表（来自风险矩阵）
A_LEVEL_MODULES = {
    "seal-engine", "pdf-renderer", "auth", "file-io",
    "llm-agent", "models", "document-state-machine"
}

# Spec frontmatter必填字段
REQUIRED_FM_FIELDS = {"spec_id", "title", "module", "level", "status", "owner", "version"}

# 特例：目录→模块映射（用于新增文件）
DIR_EXCEPTIONS = {
    "app/routes/contracts/": "document-state-machine",
}


def get_changed_files():
    """从dorny/paths-filter获取变更文件列表"""
    raw = os.environ.get("CHANGED_FILES", "[]")
    try:
        files = json.loads(raw)
        if isinstance(files, str):
            files = json.loads(files)
        return [f.strip() for f in files if f.strip()]
    except (json.JSONDecodeError, TypeError):
        print(f"⚠️ CHANGED_FILES解析失败: {raw[:200]}")
        return []


def get_pr_labels():
    """获取PR标签列表"""
    raw = os.environ.get("PR_LABELS", "[]")
    try:
        labels = json.loads(raw)
        if isinstance(labels, str):
            labels = json.loads(labels)
        return set(labels)
    except (json.JSONDecodeError, TypeError):
        return set()


def identify_affected_modules(changed_files):
    """从变更文件识别受影响的模块（精确文件匹配 + 受控特例）"""
    affected = set()
    unmatched = []
    for f in changed_files:
        # 1. 精确匹配
        if f in FILE_TO_MODULE:
            affected.add(FILE_TO_MODULE[f])
            continue

        # 2. 受控特例（仅contracts/目录下的新增文件）
        matched = False
        for dir_prefix, module_name in DIR_EXCEPTIONS.items():
            if f.startswith(dir_prefix):
                affected.add(module_name)
                matched = True
                break

        if not matched:
            unmatched.append(f)

    return affected, unmatched


def parse_spec_frontmatter(spec_path):
    """解析Spec文件的YAML frontmatter"""
    try:
        content = Path(spec_path).read_text(encoding="utf-8")
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            return None, "无frontmatter"
        fm = yaml.safe_load(fm_match.group(1))
        return fm, None
    except yaml.YAMLError as e:
        return None, f"YAML解析失败: {e}"
    except Exception as e:
        return None, str(e)


def validate_spec(spec_path, affected_modules):
    """校验单个Spec文件，返回(errors, warnings)"""
    errors = []
    warnings = []

    fm, err = parse_spec_frontmatter(spec_path)
    if err:
        errors.append(f"frontmatter: {err}")
        return errors, warnings
    if fm is None:
        errors.append("无frontmatter")
        return errors, warnings

    # 检查必填字段
    missing = REQUIRED_FM_FIELDS - set(fm.keys())
    if missing:
        errors.append(f"frontmatter缺少必填字段: {missing}")

    # 检查status有效性
    status = fm.get("status", "")
    valid_statuses = {"draft", "confirmed", "deprecated", "superseded"}
    if status not in valid_statuses:
        errors.append(f"status '{status}' 无效，允许: {valid_statuses}")
    if status in ("deprecated", "superseded"):
        errors.append(f"status为{status}，不可引用")
    if status == "draft":
        warnings.append("Spec status为draft，建议确认后再引用")

    # 检查module与变更文件是否匹配
    spec_module = fm.get("module", "")
    if spec_module and spec_module not in affected_modules:
        spec_level = fm.get("level", "B")
        if spec_level == "A":
            errors.append(f"Spec module='{spec_module}' 与变更文件所属模块{affected_modules}不匹配(A级strict)")
        else:
            warnings.append(f"Spec module='{spec_module}' 与变更文件所属模块{affected_modules}不匹配(B级warn)")

    # 检查level有效性
    level = fm.get("level", "")
    if level not in {"A", "B", "C"}:
        errors.append(f"level '{level}' 无效，允许: A/B/C")

    # 检查A级候选的level_override
    if fm.get("level_override"):
        override = fm["level_override"]
        if not re.match(r'^A\s*\(', override):
            warnings.append(f"level_override '{override}' 格式建议: 'A (复核通过 YYYY-MM-DD)'")

    return errors, warnings


def extract_spec_refs(pr_body):
    """从PR描述中提取Spec引用"""
    if not pr_body:
        return []
    # 匹配 Spec: sdd/xxx/yyy 或裸sdd/路径
    pattern = r'sdd/(?:domain-spec|change-log|enterprise-spec)/[^\s\)\]"\'<>]+\.md'
    return list(set(re.findall(pattern, pr_body)))


def main():
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))

    # 1. 获取变更文件
    changed_files = get_changed_files()
    if not changed_files:
        print("ℹ️ 无变更文件或解析失败，跳过Spec检查")
        return 0

    print(f"📋 变更文件 ({len(changed_files)}):")
    for f in changed_files:
        print(f"   {f}")

    # 2. 检查PR标签
    labels = get_pr_labels()
    if "hotfix-emergency" in labels:
        print("⚠️ hotfix-emergency标签 → 豁免Spec检查（72小时内补Spec，由hotfix_tracker追踪）")
        return 0
    if "docs-only" in labels or "dependency-bump" in labels:
        print("✅ docs-only/dependency-bump标签 → 豁免")
        return 0

    # 3. 识别受影响模块
    affected_modules, unmatched = identify_affected_modules(changed_files)
    print(f"\n📦 受影响模块: {affected_modules or '无（非业务代码）'}")

    # 未匹配的业务文件 → 阻断（V4反馈：不能只warn）
    # 受保护路径下的未匹配文件必须显式归属
    PROTECTED_PREFIXES = ("app/routes/", "app/services/", "app/models.py", "app/schema.py", "app/auth.py")
    unmatched_protected = [f for f in unmatched if any(f.startswith(p) for p in PROTECTED_PREFIXES)]
    if unmatched_protected:
        print(f"\n❌ 受保护路径下有未匹配文件（新增文件必须更新module_paths.json）:")
        for f in unmatched_protected:
            print(f"   {f}")
        print(f"\n   修法: 在 sdd/scripts/module_paths.json 中为这些文件添加模块归属")
        return 1

    if not affected_modules:
        print("✅ 无业务模块受影响，豁免Spec检查")
        return 0

    # 4. 提取PR描述中的Spec引用
    pr_body = os.environ.get("PR_BODY", "")
    spec_refs = extract_spec_refs(pr_body)

    if not spec_refs:
        print(f"\n❌ 业务代码变更未引用任何 sdd/ Spec文件")
        print(f"   受影响模块: {affected_modules}")
        print(f"   请在PR描述中添加:")
        print(f"   Spec: sdd/domain-spec/<module>/spec.md")
        print(f"   或使用标签 hotfix-emergency / docs-only / dependency-bump 豁免")
        return 1

    print(f"\n📄 Spec引用 ({len(spec_refs)}):")
    for ref in spec_refs:
        print(f"   {ref}")

    # 5. 验证Spec文件存在性
    missing_specs = []
    for ref in spec_refs:
        spec_path = workspace / ref
        if not spec_path.exists():
            missing_specs.append(ref)

    if missing_specs:
        print(f"\n❌ Spec文件不存在:")
        for s in missing_specs:
            print(f"   {s}")
        return 1

    # 6. 校验Spec frontmatter
    all_errors = []
    all_warnings = []

    for ref in spec_refs:
        spec_path = workspace / ref
        errors, warnings = validate_spec(spec_path, affected_modules)
        all_errors.extend([f"{ref}: {e}" for e in errors])
        all_warnings.extend([f"{ref}: {w}" for w in warnings])

    if all_warnings:
        print(f"\n⚠️ 警告 ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"   {w}")

    if all_errors:
        print(f"\n❌ Spec校验失败 ({len(all_errors)}):")
        for e in all_errors:
            print(f"   {e}")
        return 1

    # 7. 检查A级模块是否有Spec覆盖
    affected_a_modules = affected_modules & A_LEVEL_MODULES
    if affected_a_modules:
        covered_modules = set()
        for ref in spec_refs:
            spec_path = workspace / ref
            fm, _ = parse_spec_frontmatter(spec_path)
            if fm and fm.get("module") in affected_a_modules:
                covered_modules.add(fm.get("module"))

        uncovered = affected_a_modules - covered_modules
        if uncovered:
            print(f"\n❌ A级模块缺少Spec覆盖: {uncovered}")
            print(f"   A级模块变更必须有对应Spec文件")
            return 1

    print(f"\n✅ SDD Spec检查通过")
    print(f"   模块: {affected_modules}")
    print(f"   Spec: {spec_refs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
