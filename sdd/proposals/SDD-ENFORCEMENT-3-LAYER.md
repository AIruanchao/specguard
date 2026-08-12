# SDD强制拦截方案 — 3层物理阻断

> **当前状态**: 有效拦截率2/8=25%，cursor/coder可自由绕过SDD
> **目标**: 有效拦截率8/8=100%，cursor/coder代码级强制无法绕过

---

## 一、CI failure根因（已查明）

| 仓库 | 失败步骤 | 根因 |
|------|---------|------|
| SpecGuard | Coverage gate | `.venv/bin/python`在CI环境(ubuntu)不存在，CI用自己的python |
| 商务系统 | Install dependencies | requirements.txt缺包或安装失败 |

### 修复
- SpecGuard CI: 把`.venv/bin/python`改为`python`（CI环境用系统python）
- 商务CI: 检查requirements.txt完整性

---

## 二、3层拦截方案

### 第1层：pre-commit hook（写代码时拦截）

**作用**: cursor/coder commit时，检查改动的.py/.tsx文件有没有对应spec

**安装位置**: 每个仓库的`.git/hooks/pre-commit`

**脚本逻辑**:
```bash
#!/bin/bash
# SDD pre-commit hook
# 检查：改了代码文件但sdd/目录没有对应spec → 阻断commit

CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|tsx|ts)$' | grep -v test | grep -v __pycache__)
SPEC_CHANGED=$(git diff --cached --name-only | grep -c 'sdd/')

if [ -n "$CHANGED_FILES" ] && [ "$SPEC_CHANGED" -eq 0 ]; then
    echo "⚠️ SDD拦截: 改了代码但没改spec"
    echo "改动的文件:"
    echo "$CHANGED_FILES"
    echo ""
    echo "请在sdd/domain-spec/下添加或更新对应spec.md"
    echo "或用 SDD_SKIP=1 git commit 跳过(仅限紧急修复)"
    exit 1
fi
```

**跳过机制**: `SDD_SKIP=1 git commit`（紧急修复用，72h内补spec）

### 第2层：任务卡Phase 0 spec检查（派活时拦截）

**作用**: run-coder-task.sh开头检查任务卡是否引用spec

**修改位置**: `~/.hermes/scripts/run-coder-task.sh`

**新增Phase 0**:
```bash
# ===== Phase 0: SDD Spec检查 =====
TASK_FILE="$1"
if grep -q "sdd/" "$TASK_FILE" || grep -q "spec.md" "$TASK_FILE"; then
    echo "[Phase 0] ✅ 任务卡引用了SDD spec"
else
    # 检查是否是运维/配置类任务（不需要spec）
    if grep -qE "(deploy|config|ssh|cron|launchd|nginx|docker)" "$TASK_FILE"; then
        echo "[Phase 0] ⏭️ 运维任务，跳过spec检查"
    else
        echo "[Phase 0] ❌ 任务卡未引用sdd/或spec.md"
        echo "[Phase 0] 拒绝执行。请在任务卡中添加sdd/domain-spec/xxx/spec.md引用"
        exit 1
    fi
fi
```

### 第3层：CI门禁修复（合并时拦截）

**SpecGuard CI修复**:
```yaml
# 原来（错）:
- run: .venv/bin/python -m pytest ...
# 改为:
- run: python -m pytest ...
```

**商务CI修复**: 检查requirements.txt，确保CI环境可安装

**Branch protection扩展**: 7个仓库全部配置required status checks

---

## 三、实施计划

| 步骤 | 动作 | 工作量 | 执行者 |
|------|------|--------|--------|
| 1 | 写pre-commit hook脚本 | 10min | cursor |
| 2 | 安装到7个仓库 | 10min | 大锤80 |
| 3 | run-coder-task.sh加Phase 0 | 10min | cursor |
| 4 | SpecGuard CI修`.venv`路径 | 5min | 大锤80 |
| 5 | 商务CI修dependencies | 10min | 大锤80 |
| 6 | 7仓库配branch protection | 15min | 大锤80 |
| 7 | 验证：cursor/coder被拦截 | 10min | 大锤80 |

**总工作量: 70min**

---

## 四、验收标准

| 验收项 | 标准 |
|--------|------|
| pre-commit hook | 7/7仓库安装 |
| 任务卡Phase 0 | 无spec的任务卡被REFUSED |
| CI SpecGuard | conclusion=success |
| CI 商务 | conclusion=success |
| Branch protection | 7/7仓库 |
| 拦截测试 | 改代码不写spec → commit被阻断 |

**完成后拦截率: 2/8 → 8/8 = 100%**
