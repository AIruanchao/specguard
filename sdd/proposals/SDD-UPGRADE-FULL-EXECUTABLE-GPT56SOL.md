# SDD升级全量可执行方案（P0-P3）

## 一、目标与执行基线

### 1. 阶段目标

| 阶段 | 周期 | 核心目标 |
|---|---:|---|
| P0 | 14天 | 建立统一SDD清单、可追溯规则、测试基线和CI阻断机制 |
| P1 | 14天 | 补齐核心测试、提高覆盖率、完成7系统统一验收与生产发布 |
| P2 | 4周 | 建立跨系统依赖、变更影响分析、质量看板和自动发布 |
| P3 | 4周 | 推进SDD平台化、策略治理、生产观测和持续改进 |

### 2. P0/P1质量目标

| 系统 | 当前覆盖率 | P0目标 | P1目标 |
|---|---:|---:|---:|
| business-api | 45% | ≥50% | ≥65% |
| specguard | 81% | ≥81%且不得下降 | ≥85% |
| dh-factory | 32% | ≥40% | ≥55% |
| erp-web | 未测 | 建立基线 | ≥50% |
| stock-api | 未测 | 建立基线 | ≥55% |
| ledger | 未测 | 建立基线 | ≥50% |
| specguard-cloud3 | - | 完成部署前检查 | 完成灰度和回滚验证 |

### 3. 统一SDD最小字段

每个有效SDD必须包含以下字段或章节：

```markdown
# SDD-<系统>-<编号>: <标题>

- Status: draft|review|approved|implemented|verified|deprecated
- Owner: <负责人>
- Priority: P0|P1|P2|P3
- Requirement: <需求编号>
- Last-Updated: YYYY-MM-DD

## Context
## Scope
## Non-Goals
## Design
## Interfaces
## Acceptance Criteria
## Test Mapping
## Rollback
```

### 4. 执行约束

- 大锤80：范围确认、跨系统协调、验收、生产变更批准。
- cursor：文档整理、CI配置、批量迁移、前端测试。
- coder：测试实现、校验器开发、后端和脚本改造。
- 所有新增CI先以告警模式运行，基线稳定后切换阻断模式。
- 禁止直接在`cloud3`生产目录修改代码；必须通过镜像、发布包或可回滚同步流程部署。

---

# P0：基础治理与CI闭环（14天）

## P0-D1：全系统基线冻结

### P0-D1-T1 全量仓库状态和SDD清单采集｜执行者：大锤80

**Shell命令**

```bash
mkdir -p /Users/maccc/projects/specguard/artifacts/p0/baseline

for repo in \
  /Users/maccc/projects/business-document-generator \
  /Users/maccc/projects/specguard \
  /Users/maccc/daily_stock_analysis \
  /Users/maccc/Projects/ledger-quality-system
do
  name="$(basename "$repo")"
  git -C "$repo" status --short \
    > "/Users/maccc/projects/specguard/artifacts/p0/baseline/${name}-git-status.txt"
  git -C "$repo" rev-parse HEAD \
    > "/Users/maccc/projects/specguard/artifacts/p0/baseline/${name}-commit.txt"
  find "$repo" -type f \( -iname '*sdd*.md' -o -path '*/specs/*.md' -o -path '*/sdd/*.md' \) \
    | sort > "/Users/maccc/projects/specguard/artifacts/p0/baseline/${name}-sdd-files.txt"
done

ssh MacMini '
  cd /Users/mac/erp-project &&
  git status --short &&
  git rev-parse HEAD &&
  find . -type f \( -iname "*sdd*.md" -o -path "*/specs/*.md" -o -path "*/sdd/*.md" \) | sort
' > /Users/maccc/projects/specguard/artifacts/p0/baseline/erp-web-baseline.txt

ssh cloud3 '
  cd /opt/specguard &&
  docker compose ps &&
  git rev-parse HEAD 2>/dev/null || true
' > /Users/maccc/projects/specguard/artifacts/p0/baseline/specguard-cloud3-baseline.txt
```

**产出文件**

- `artifacts/p0/baseline/*-git-status.txt`
- `artifacts/p0/baseline/*-commit.txt`
- `artifacts/p0/baseline/*-sdd-files.txt`
- `artifacts/p0/baseline/erp-web-baseline.txt`
- `artifacts/p0/baseline/specguard-cloud3-baseline.txt`

**验收命令与预期**

```bash
find /Users/maccc/projects/specguard/artifacts/p0/baseline -type f -size +0 | wc -l
```

预期：不少于`15`个非空基线文件，7个系统均有记录。

**依赖**

- 本机能够访问4个本地仓库。
- `ssh MacMini`、`ssh cloud3`免密或可正常认证。

**时间**

`4h`

---

## P0-D2：business-api测试基线

### P0-D2-T1 建立商务单据测试和覆盖率基线｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/projects/business-document-generator
mkdir -p artifacts/test-baseline
.venv/bin/python -m pip install -U pytest pytest-cov
set +e
.venv/bin/python -m pytest \
  --cov=. \
  --cov-report=term-missing \
  --cov-report=xml:artifacts/test-baseline/coverage.xml \
  --junitxml=artifacts/test-baseline/junit.xml \
  2>&1 | tee artifacts/test-baseline/pytest.txt
test_rc=${PIPESTATUS[0]}
set -e
printf '%s\n' "$test_rc" > artifacts/test-baseline/exit-code.txt
```

**产出文件**

- `artifacts/test-baseline/coverage.xml`
- `artifacts/test-baseline/junit.xml`
- `artifacts/test-baseline/pytest.txt`
- `artifacts/test-baseline/exit-code.txt`

**验收命令与预期**

```bash
cd /Users/maccc/projects/business-document-generator
.venv/bin/python - <<'PY'
import xml.etree.ElementTree as ET
root = ET.parse("artifacts/test-baseline/coverage.xml").getroot()
print(round(float(root.attrib["line-rate"]) * 100, 2))
PY
```

预期：成功输出覆盖率，基线约`45%`；测试失败项已在`junit.xml`中可定位。

**依赖**

- P0-D1-T1。
- `.venv/bin/python`可执行。

**时间**

`5h`

---

## P0-D3：specguard自检基线

### P0-D3-T1 固化SpecGuard测试与规则基线｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p artifacts/p0/specguard-baseline
.venv/bin/python -m pip install -U pytest pytest-cov
.venv/bin/python -m pytest \
  --cov=. \
  --cov-report=term-missing \
  --cov-report=xml:artifacts/p0/specguard-baseline/coverage.xml \
  --junitxml=artifacts/p0/specguard-baseline/junit.xml \
  | tee artifacts/p0/specguard-baseline/pytest.txt
cp .github/workflows/ci.yml artifacts/p0/specguard-baseline/ci.yml
```

**产出文件**

- `artifacts/p0/specguard-baseline/coverage.xml`
- `artifacts/p0/specguard-baseline/junit.xml`
- `artifacts/p0/specguard-baseline/ci.yml`
- `artifacts/p0/specguard-baseline/pytest.txt`

**验收命令与预期**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python -m pytest --cov=. --cov-fail-under=81 -q
```

预期：退出码`0`，覆盖率不低于`81%`。

**依赖**

- P0-D1-T1。

**时间**

`4h`

---

## P0-D4：dh-factory测试基线

### P0-D4-T1 固化DH工厂Python和Shell测试基线｜执行者：coder

**Shell命令**

```bash
ssh root@localhost 'true' 2>/dev/null || true
cd /opt/dh-enterprise-factory
mkdir -p artifacts/p0/test-baseline
python3 -m pip install --user pytest pytest-cov
set +e
python3 -m pytest \
  --cov=. \
  --cov-report=xml:artifacts/p0/test-baseline/coverage.xml \
  --junitxml=artifacts/p0/test-baseline/junit.xml \
  2>&1 | tee artifacts/p0/test-baseline/pytest.txt
test_rc=${PIPESTATUS[0]}
find . -type f -name '*.sh' -print0 \
  | xargs -0 -r shellcheck \
  > artifacts/p0/test-baseline/shellcheck.txt 2>&1
shell_rc=$?
set -e
printf 'pytest=%s\nshellcheck=%s\n' "$test_rc" "$shell_rc" \
  > artifacts/p0/test-baseline/exit-codes.txt
```

**产出文件**

- `/opt/dh-enterprise-factory/artifacts/p0/test-baseline/coverage.xml`
- `/opt/dh-enterprise-factory/artifacts/p0/test-baseline/junit.xml`
- `/opt/dh-enterprise-factory/artifacts/p0/test-baseline/shellcheck.txt`
- `/opt/dh-enterprise-factory/artifacts/p0/test-baseline/exit-codes.txt`

**验收命令与预期**

```bash
cd /opt/dh-enterprise-factory
python3 - <<'PY'
import xml.etree.ElementTree as ET
root = ET.parse("artifacts/p0/test-baseline/coverage.xml").getroot()
print(round(float(root.attrib["line-rate"]) * 100, 2))
PY
```

预期：输出覆盖率，基线约`32%`；Shell问题形成可执行清单。

**依赖**

- 当前账号对`/opt/dh-enterprise-factory`有写权限。
- 已安装或可安装`shellcheck`。

**时间**

`5h`

---

## P0-D5：erp-web测试基线

### P0-D5-T1 建立ERP Vitest基线｜执行者：cursor

**Shell命令**

```bash
ssh MacMini '
  set -e
  cd /Users/mac/erp-project
  mkdir -p artifacts/p0/test-baseline
  npm ci
  set +e
  npm test -- --run --coverage \
    2>&1 | tee artifacts/p0/test-baseline/vitest.txt
  rc=${PIPESTATUS[0]}
  set -e
  printf "%s\n" "$rc" > artifacts/p0/test-baseline/exit-code.txt
  test -f coverage/coverage-summary.json &&
    cp coverage/coverage-summary.json artifacts/p0/test-baseline/coverage-summary.json ||
    true
'
```

**产出文件**

- `/Users/mac/erp-project/artifacts/p0/test-baseline/vitest.txt`
- `/Users/mac/erp-project/artifacts/p0/test-baseline/exit-code.txt`
- `/Users/mac/erp-project/artifacts/p0/test-baseline/coverage-summary.json`

**验收命令与预期**

```bash
ssh MacMini '
  cd /Users/mac/erp-project &&
  node -e "
    const c=require(\"./artifacts/p0/test-baseline/coverage-summary.json\");
    console.log(c.total.lines.pct)
  "
'
```

预期：输出ERP当前行覆盖率；若原配置未开启覆盖率，由当日任务补充`@vitest/coverage-v8`和Vitest覆盖率配置。

**依赖**

- `ssh MacMini`可用。
- MacMini安装Node.js和npm。

**时间**

`5h`

---

## P0-D6：stock-api测试基线

### P0-D6-T1 建立股票仪表盘测试基线｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/daily_stock_analysis
mkdir -p artifacts/p0/test-baseline
python3 -m pip install --user pytest pytest-cov
set +e
python3 -m pytest \
  --cov=. \
  --cov-report=xml:artifacts/p0/test-baseline/coverage.xml \
  --junitxml=artifacts/p0/test-baseline/junit.xml \
  2>&1 | tee artifacts/p0/test-baseline/pytest.txt
rc=${PIPESTATUS[0]}
set -e
printf '%s\n' "$rc" > artifacts/p0/test-baseline/exit-code.txt
```

**产出文件**

- `artifacts/p0/test-baseline/coverage.xml`
- `artifacts/p0/test-baseline/junit.xml`
- `artifacts/p0/test-baseline/pytest.txt`

**验收命令与预期**

```bash
cd /Users/maccc/daily_stock_analysis
python3 - <<'PY'
import xml.etree.ElementTree as ET
root = ET.parse("artifacts/p0/test-baseline/coverage.xml").getroot()
print(round(float(root.attrib["line-rate"]) * 100, 2))
PY
```

预期：输出覆盖率；所有收集失败和外部数据依赖均有明确错误记录。

**依赖**

- P0-D1-T1。

**时间**

`5h`

---

## P0-D7：ledger测试基线

### P0-D7-T1 建立台账系统测试和飞书依赖基线｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/Projects/ledger-quality-system
mkdir -p artifacts/p0/test-baseline
.venv/bin/python -m pip install -U pytest pytest-cov
set +e
.venv/bin/python -m pytest \
  --cov=. \
  --cov-report=xml:artifacts/p0/test-baseline/coverage.xml \
  --junitxml=artifacts/p0/test-baseline/junit.xml \
  2>&1 | tee artifacts/p0/test-baseline/pytest.txt
rc=${PIPESTATUS[0]}
set -e
printf '%s\n' "$rc" > artifacts/p0/test-baseline/exit-code.txt
env | cut -d= -f1 | sort \
  | grep -E 'FEISHU|LARK|APP_ID|APP_SECRET' \
  > artifacts/p0/test-baseline/external-env-names.txt || true
```

**产出文件**

- `artifacts/p0/test-baseline/coverage.xml`
- `artifacts/p0/test-baseline/junit.xml`
- `artifacts/p0/test-baseline/external-env-names.txt`
- `artifacts/p0/test-baseline/pytest.txt`

**验收命令与预期**

```bash
cd /Users/maccc/Projects/ledger-quality-system
.venv/bin/python -m pytest --collect-only -q
```

预期：测试可收集；测试阶段不真实调用飞书生产接口。

**依赖**

- P0-D1-T1。
- `.venv/bin/python`可执行。

**时间**

`5h`

---

## P0-D8：统一SDD校验器

### P0-D8-T1 实现统一SDD schema和CLI校验器｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p schemas tools tests/fixtures/sdd
cursor schemas/sdd.schema.yaml tools/sdd_gate.py tests/test_sdd_gate.py
.venv/bin/python -m pytest tests/test_sdd_gate.py -q
.venv/bin/python tools/sdd_gate.py \
  --root /Users/maccc/projects/business-document-generator \
  --report artifacts/p0/business-sdd-report.json
.venv/bin/python tools/sdd_gate.py \
  --root /Users/maccc/projects/specguard \
  --report artifacts/p0/specguard-sdd-report.json
```

**产出文件**

- `schemas/sdd.schema.yaml`
- `tools/sdd_gate.py`
- `tests/test_sdd_gate.py`
- `artifacts/p0/business-sdd-report.json`
- `artifacts/p0/specguard-sdd-report.json`

**验收命令与预期**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python -m pytest tests/test_sdd_gate.py -q
.venv/bin/python tools/sdd_gate.py --help
```

预期：单元测试全部通过；CLI支持`--root`、`--report`、`--changed-only`和`--strict`。

**依赖**

- P0-D2-T1、P0-D3-T1。
- 大锤80确认统一SDD最小字段。

**时间**

`7h`

---

## P0-D9：business-api接入SDD Gate

### P0-D9-T1 商务单据CI增加SDD和覆盖率门禁｜执行者：cursor

**Shell命令**

```bash
cd /Users/maccc/projects/business-document-generator
mkdir -p tools schemas
cp /Users/maccc/projects/specguard/tools/sdd_gate.py tools/sdd_gate.py
cp /Users/maccc/projects/specguard/schemas/sdd.schema.yaml schemas/sdd.schema.yaml
cursor .github/workflows/ci.yml
.venv/bin/python tools/sdd_gate.py --root . --report artifacts/sdd-report.json
.venv/bin/python -m pytest --cov=. --cov-fail-under=50 -q
git diff --check
```

**产出文件**

- `tools/sdd_gate.py`
- `schemas/sdd.schema.yaml`
- `.github/workflows/ci.yml`
- `artifacts/sdd-report.json`

**验收命令与预期**

```bash
cd /Users/maccc/projects/business-document-generator
.venv/bin/python tools/sdd_gate.py --root . --strict
.venv/bin/python -m pytest --cov=. --cov-fail-under=50 -q
```

预期：两条命令退出码均为`0`；CI包含`sdd-gate`和`test`作业。

**依赖**

- P0-D8-T1。
- 覆盖率补到`50%`所需的最低限度测试。

**时间**

`7h`

---

## P0-D10：SpecGuard自托管门禁

### P0-D10-T1 SpecGuard CI使用自身规则校验自身SDD｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
cursor .github/workflows/ci.yml
.venv/bin/python tools/sdd_gate.py --root . --strict \
  --report artifacts/p0/specguard-self-gate.json
.venv/bin/python -m pytest --cov=. --cov-fail-under=81 -q
git diff --check
```

**产出文件**

- 更新后的`.github/workflows/ci.yml`
- `artifacts/p0/specguard-self-gate.json`
- `docs/sdd/`中修正后的9份SDD或现有SDD目录中的等价文件

**验收命令与预期**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python tools/sdd_gate.py --root . --strict
.venv/bin/python -m pytest --cov=. --cov-fail-under=81 -q
```

预期：退出码均为`0`；缺字段SDD能够让CI失败。

**依赖**

- P0-D8-T1。

**时间**

`6h`

---

## P0-D11：dh-factory门禁升级

### P0-D11-T1 DH工厂接入SDD、Python和Shell三重门禁｜执行者：coder

**Shell命令**

```bash
cd /opt/dh-enterprise-factory
mkdir -p tools schemas
cp /Users/maccc/projects/specguard/tools/sdd_gate.py tools/sdd_gate.py
cp /Users/maccc/projects/specguard/schemas/sdd.schema.yaml schemas/sdd.schema.yaml
cursor .github/workflows/sdd-gate.yml
python3 tools/sdd_gate.py --root . --report artifacts/p0/sdd-report.json
python3 -m pytest --cov=. --cov-fail-under=40 -q
find . -type f -name '*.sh' -print0 | xargs -0 -r shellcheck
git diff --check
```

**产出文件**

- `/opt/dh-enterprise-factory/tools/sdd_gate.py`
- `/opt/dh-enterprise-factory/schemas/sdd.schema.yaml`
- `/opt/dh-enterprise-factory/.github/workflows/sdd-gate.yml`
- `/opt/dh-enterprise-factory/artifacts/p0/sdd-report.json`

**验收命令与预期**

```bash
cd /opt/dh-enterprise-factory
python3 tools/sdd_gate.py --root . --strict
python3 -m pytest --cov=. --cov-fail-under=40 -q
find . -type f -name '*.sh' -print0 | xargs -0 -r shellcheck
```

预期：全部退出码为`0`；覆盖率不低于`40%`。

**依赖**

- P0-D4-T1、P0-D8-T1。

**时间**

`7h`

---

## P0-D12：erp-web CI建设

### P0-D12-T1 新建ERP Vitest和SDD CI｜执行者：cursor

**Shell命令**

```bash
scp /Users/maccc/projects/specguard/tools/sdd_gate.py \
  MacMini:/Users/mac/erp-project/tools/sdd_gate.py
scp /Users/maccc/projects/specguard/schemas/sdd.schema.yaml \
  MacMini:/Users/mac/erp-project/schemas/sdd.schema.yaml

ssh MacMini '
  set -e
  cd /Users/mac/erp-project
  mkdir -p .github/workflows artifacts/p0
  cursor .github/workflows/ci.yml vitest.config.*
  npm ci
  npm test -- --run --coverage
  python3 tools/sdd_gate.py --root . --strict --report artifacts/p0/sdd-report.json
  git diff --check
'
```

**产出文件**

- `/Users/mac/erp-project/.github/workflows/ci.yml`
- `/Users/mac/erp-project/tools/sdd_gate.py`
- `/Users/mac/erp-project/schemas/sdd.schema.yaml`
- `/Users/mac/erp-project/artifacts/p0/sdd-report.json`

**验收命令与预期**

```bash
ssh MacMini '
  cd /Users/mac/erp-project &&
  npm test -- --run --coverage &&
  python3 tools/sdd_gate.py --root . --strict
'
```

预期：退出码`0`；CI覆盖`npm ci`、Vitest、SDD Gate和Prisma schema校验。

**依赖**

- P0-D5-T1、P0-D8-T1。
- MacMini可使用`python3`。

**时间**

`7h`

---

## P0-D13：stock-api CI建设

### P0-D13-T1 股票仪表盘新增CI和外部数据隔离｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/daily_stock_analysis
mkdir -p .github/workflows tools schemas artifacts/p0
cp /Users/maccc/projects/specguard/tools/sdd_gate.py tools/sdd_gate.py
cp /Users/maccc/projects/specguard/schemas/sdd.schema.yaml schemas/sdd.schema.yaml
cursor .github/workflows/ci.yml pytest.ini tests/conftest.py
python3 tools/sdd_gate.py --root . --strict --report artifacts/p0/sdd-report.json
python3 -m pytest --cov=. --cov-report=xml --cov-fail-under=1 -q
git diff --check
```

**产出文件**

- `.github/workflows/ci.yml`
- `tools/sdd_gate.py`
- `schemas/sdd.schema.yaml`
- `pytest.ini`
- `tests/conftest.py`
- `artifacts/p0/sdd-report.json`

**验收命令与预期**

```bash
cd /Users/maccc/daily_stock_analysis
env -u TUSHARE_TOKEN -u ALPHA_VANTAGE_API_KEY \
  python3 -m pytest --cov=. -q
python3 tools/sdd_gate.py --root . --strict
```

预期：无真实行情密钥时测试仍可完成；CI已建立，SDD Gate通过。

**依赖**

- P0-D6-T1、P0-D8-T1。

**时间**

`7h`

---

## P0-D14：ledger CI与P0总验收

### P0-D14-T1 台账CI建设并完成P0统一验收｜执行者：大锤80

**Shell命令**

```bash
cd /Users/maccc/Projects/ledger-quality-system
mkdir -p .github/workflows tools schemas artifacts/p0
cp /Users/maccc/projects/specguard/tools/sdd_gate.py tools/sdd_gate.py
cp /Users/maccc/projects/specguard/schemas/sdd.schema.yaml schemas/sdd.schema.yaml
cursor .github/workflows/ci.yml tests/conftest.py
.venv/bin/python tools/sdd_gate.py --root . --strict \
  --report artifacts/p0/sdd-report.json
.venv/bin/python -m pytest --cov=. --cov-report=xml -q
git diff --check

cd /Users/maccc/projects/specguard
mkdir -p artifacts/p0/final
cursor artifacts/p0/final/P0-ACCEPTANCE.md
```

**产出文件**

- `/Users/maccc/Projects/ledger-quality-system/.github/workflows/ci.yml`
- `/Users/maccc/Projects/ledger-quality-system/tools/sdd_gate.py`
- `/Users/maccc/Projects/ledger-quality-system/schemas/sdd.schema.yaml`
- `/Users/maccc/Projects/ledger-quality-system/artifacts/p0/sdd-report.json`
- `/Users/maccc/projects/specguard/artifacts/p0/final/P0-ACCEPTANCE.md`

**验收命令与预期**

```bash
test -f /Users/maccc/projects/business-document-generator/.github/workflows/ci.yml
test -f /Users/maccc/projects/specguard/.github/workflows/ci.yml
test -f /opt/dh-enterprise-factory/.github/workflows/sdd-gate.yml
ssh MacMini 'test -f /Users/mac/erp-project/.github/workflows/ci.yml'
test -f /Users/maccc/daily_stock_analysis/.github/workflows/ci.yml
test -f /Users/maccc/Projects/ledger-quality-system/.github/workflows/ci.yml
```

预期：6个开发仓库全部具备CI；P0验收报告记录覆盖率、SDD通过率、遗留问题和责任人。

**依赖**

- P0-D9至P0-D13全部完成。

**时间**

`7h`

---

# P1：覆盖率提升与生产闭环（14天）

## P1-D1：business-api核心服务测试

### P1-D1-T1 补齐商务单据核心业务测试｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/projects/business-document-generator
cursor tests
.venv/bin/python -m pytest tests -q \
  --cov=. \
  --cov-report=term-missing \
  --cov-report=xml:artifacts/p1-business-coverage.xml \
  --cov-fail-under=58
```

**产出文件**

- `tests/`新增或更新的服务层、API层测试
- `artifacts/p1-business-coverage.xml`

**验收命令与预期**

```bash
cd /Users/maccc/projects/business-document-generator
.venv/bin/python -m pytest --cov=. --cov-fail-under=58 -q
```

预期：退出码`0`，覆盖率不低于`58%`。

**依赖**

- P0-D9-T1。

**时间**

`7h`

---

## P1-D2：business-api追溯闭环

### P1-D2-T1 建立42份SDD到测试用例映射｜执行者：cursor

**Shell命令**

```bash
cd /Users/maccc/projects/business-document-generator
mkdir -p artifacts/p1
cursor docs tests
.venv/bin/python tools/sdd_gate.py \
  --root . \
  --strict \
  --require-test-mapping \
  --report artifacts/p1/sdd-traceability.json
.venv/bin/python -m pytest --cov=. --cov-fail-under=65 -q
```

**产出文件**

- 修正后的42份SDD
- `artifacts/p1/sdd-traceability.json`
- 新增验收测试

**验收命令与预期**

```bash
cd /Users/maccc/projects/business-document-generator
.venv/bin/python tools/sdd_gate.py --root . --strict --require-test-mapping
.venv/bin/python -m pytest --cov=. --cov-fail-under=65 -q
```

预期：42份SDD均有测试映射；覆盖率不低于`65%`。

**依赖**

- P1-D1-T1。

**时间**

`7h`

---

## P1-D3：SpecGuard覆盖率提升

### P1-D3-T1 补齐校验器边界和失败路径测试｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
cursor tests/test_sdd_gate.py tests
.venv/bin/python -m pytest \
  --cov=. \
  --cov-report=term-missing \
  --cov-report=xml:artifacts/p1-specguard-coverage.xml \
  --cov-fail-under=85 \
  -q
```

**产出文件**

- SDD解析异常、字段缺失、编码、changed-only相关测试
- `artifacts/p1-specguard-coverage.xml`

**验收命令与预期**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python -m pytest --cov=. --cov-fail-under=85 -q
```

预期：退出码`0`；覆盖率不低于`85%`。

**依赖**

- P0-D10-T1。

**时间**

`6h`

---

## P1-D4：SpecGuard规则版本化

### P1-D4-T1 增加规则版本、兼容性和抑制机制｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
cursor schemas/sdd.schema.yaml tools/sdd_gate.py tests/test_sdd_gate.py docs
.venv/bin/python -m pytest tests/test_sdd_gate.py -q
.venv/bin/python tools/sdd_gate.py \
  --root . \
  --schema-version v1 \
  --strict \
  --report artifacts/p1-rule-v1.json
```

**产出文件**

- `schemas/sdd.schema.yaml`规则版本定义
- `docs/SDD-RULES.md`
- 抑制规则及其测试
- `artifacts/p1-rule-v1.json`

**验收命令与预期**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python tools/sdd_gate.py --root . --schema-version v1 --strict
.venv/bin/python -m pytest --cov=. --cov-fail-under=85 -q
```

预期：规则版本可显式选择；非法抑制会失败；合法抑制必须包含原因和到期日。

**依赖**

- P1-D3-T1。

**时间**

`7h`

---

## P1-D5：dh-factory Python测试提升

### P1-D5-T1 补齐DH工厂关键Python流程测试｜执行者：coder

**Shell命令**

```bash
cd /opt/dh-enterprise-factory
cursor tests
python3 -m pytest \
  --cov=. \
  --cov-report=term-missing \
  --cov-report=xml:artifacts/p1-dh-coverage.xml \
  --cov-fail-under=48 \
  -q
```

**产出文件**

- `tests/`新增工厂编排、配置解析、失败回滚测试
- `artifacts/p1-dh-coverage.xml`

**验收命令与预期**

```bash
cd /opt/dh-enterprise-factory
python3 -m pytest --cov=. --cov-fail-under=48 -q
```

预期：退出码`0`；覆盖率不低于`48%`。

**依赖**

- P0-D11-T1。

**时间**

`7h`

---

## P1-D6：dh-factory Shell测试与追溯

### P1-D6-T1 建立Shell回归测试并达到55%覆盖率｜执行者：coder

**Shell命令**

```bash
cd /opt/dh-enterprise-factory
mkdir -p tests/shell artifacts/p1
cursor tests/shell .github/workflows/sdd-gate.yml
find . -type f -name '*.sh' -print0 | xargs -0 -r shellcheck
command -v bats
bats tests/shell
python3 tools/sdd_gate.py \
  --root . --strict --require-test-mapping \
  --report artifacts/p1/dh-sdd-traceability.json
python3 -m pytest --cov=. --cov-fail-under=55 -q
```

**产出文件**

- `tests/shell/*.bats`
- 更新后的10份SDD
- `artifacts/p1/dh-sdd-traceability.json`

**验收命令与预期**

```bash
cd /opt/dh-enterprise-factory
bats tests/shell
python3 -m pytest --cov=. --cov-fail-under=55 -q
python3 tools/sdd_gate.py --root . --strict --require-test-mapping
```

预期：全部退出码为`0`；覆盖率不低于`55%`。

**依赖**

- P1-D5-T1。
- 安装`bats-core`。

**时间**

`7h`

---

## P1-D7：erp-web核心测试

### P1-D7-T1 补齐ERP服务、组件和Prisma测试｜执行者：cursor

**Shell命令**

```bash
ssh MacMini '
  set -e
  cd /Users/mac/erp-project
  cursor tests src app
  npm test -- --run --coverage
  npx prisma validate
  node -e "
    const c=require(\"./coverage/coverage-summary.json\");
    if (c.total.lines.pct < 45) process.exit(1);
    console.log(c.total.lines.pct);
  "
'
```

**产出文件**

- ERP服务层和组件测试
- Prisma校验测试或测试数据库配置
- `coverage/coverage-summary.json`

**验收命令与预期**

```bash
ssh MacMini '
  cd /Users/mac/erp-project &&
  npm test -- --run --coverage &&
  npx prisma validate
'
```

预期：退出码`0`；行覆盖率不低于`45%`。

**依赖**

- P0-D12-T1。

**时间**

`7h`

---

## P1-D8：erp-web SDD闭环

### P1-D8-T1 完成ERP 11份SDD追溯和50%覆盖率｜执行者：cursor

**Shell命令**

```bash
ssh MacMini '
  set -e
  cd /Users/mac/erp-project
  cursor docs tests .github/workflows/ci.yml
  python3 tools/sdd_gate.py \
    --root . --strict --require-test-mapping \
    --report artifacts/p1-erp-traceability.json
  npm test -- --run --coverage
  node -e "
    const c=require(\"./coverage/coverage-summary.json\");
    if (c.total.lines.pct < 50) process.exit(1);
  "
'
```

**产出文件**

- 修正后的11份SDD
- `/Users/mac/erp-project/artifacts/p1-erp-traceability.json`
- 更新后的CI覆盖率阈值

**验收命令与预期**

```bash
ssh MacMini '
  cd /Users/mac/erp-project &&
  python3 tools/sdd_gate.py --root . --strict --require-test-mapping &&
  npm test -- --run --coverage
'
```

预期：11份SDD全部具备测试映射；行覆盖率不低于`50%`。

**依赖**

- P1-D7-T1。

**时间**

`7h`

---

## P1-D9：stock-api核心测试

### P1-D9-T1 补齐行情、计算和API测试｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/daily_stock_analysis
cursor tests
env -u TUSHARE_TOKEN -u ALPHA_VANTAGE_API_KEY \
  python3 -m pytest \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=xml:artifacts/p1-stock-coverage.xml \
    --cov-fail-under=45 \
    -q
```

**产出文件**

- 行情适配器Mock测试
- 指标计算参数化测试
- FastAPI接口测试
- `artifacts/p1-stock-coverage.xml`

**验收命令与预期**

```bash
cd /Users/maccc/daily_stock_analysis
env -u TUSHARE_TOKEN -u ALPHA_VANTAGE_API_KEY \
  python3 -m pytest --cov=. --cov-fail-under=45 -q
```

预期：无外部密钥时退出码`0`；覆盖率不低于`45%`。

**依赖**

- P0-D13-T1。

**时间**

`7h`

---

## P1-D10：stock-api追溯闭环

### P1-D10-T1 完成股票系统7份SDD和55%覆盖率｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/daily_stock_analysis
cursor docs tests .github/workflows/ci.yml
python3 tools/sdd_gate.py \
  --root . --strict --require-test-mapping \
  --report artifacts/p1-stock-traceability.json
env -u TUSHARE_TOKEN -u ALPHA_VANTAGE_API_KEY \
  python3 -m pytest --cov=. --cov-fail-under=55 -q
```

**产出文件**

- 修正后的7份SDD
- `artifacts/p1-stock-traceability.json`
- 更新后的CI阈值

**验收命令与预期**

```bash
cd /Users/maccc/daily_stock_analysis
python3 tools/sdd_gate.py --root . --strict --require-test-mapping
env -u TUSHARE_TOKEN -u ALPHA_VANTAGE_API_KEY \
  python3 -m pytest --cov=. --cov-fail-under=55 -q
```

预期：两条命令退出码为`0`；覆盖率不低于`55%`。

**依赖**

- P1-D9-T1。

**时间**

`7h`

---

## P1-D11：ledger核心测试

### P1-D11-T1 补齐台账处理和飞书适配器测试｜执行者：coder

**Shell命令**

```bash
cd /Users/maccc/Projects/ledger-quality-system
cursor tests
env -u FEISHU_APP_ID -u FEISHU_APP_SECRET -u LARK_APP_ID -u LARK_APP_SECRET \
  .venv/bin/python -m pytest \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=xml:artifacts/p1-ledger-coverage.xml \
    --cov-fail-under=42 \
    -q
```

**产出文件**

- 飞书HTTP适配器Mock测试
- 台账校验和导入测试
- `artifacts/p1-ledger-coverage.xml`

**验收命令与预期**

```bash
cd /Users/maccc/Projects/ledger-quality-system
env -u FEISHU_APP_ID -u FEISHU_APP_SECRET \
  .venv/bin/python -m pytest --cov=. --cov-fail-under=42 -q
```

预期：不连接飞书生产环境；覆盖率不低于`42%`。

**依赖**

- P0-D14-T1。

**时间**

`7h`

---

## P1-D12：ledger追溯闭环

### P1-D12-T1 完成台账8份SDD和50%覆盖率｜执行者：cursor

**Shell命令**

```bash
cd /Users/maccc/Projects/ledger-quality-system
cursor docs tests .github/workflows/ci.yml
.venv/bin/python tools/sdd_gate.py \
  --root . --strict --require-test-mapping \
  --report artifacts/p1-ledger-traceability.json
env -u FEISHU_APP_ID -u FEISHU_APP_SECRET \
  .venv/bin/python -m pytest --cov=. --cov-fail-under=50 -q
```

**产出文件**

- 修正后的8份SDD
- `artifacts/p1-ledger-traceability.json`
- 更新后的CI阈值

**验收命令与预期**

```bash
cd /Users/maccc/Projects/ledger-quality-system
.venv/bin/python tools/sdd_gate.py --root . --strict --require-test-mapping
env -u FEISHU_APP_ID -u FEISHU_APP_SECRET \
  .venv/bin/python -m pytest --cov=. --cov-fail-under=50 -q
```

预期：8份SDD均有测试映射；覆盖率不低于`50%`。

**依赖**

- P1-D11-T1。

**时间**

`7h`

---

## P1-D13：cloud3生产预演与灰度

### P1-D13-T1 SpecGuard生产镜像备份、灰度和回滚验证｜执行者：大锤80

**Shell命令**

```bash
ssh cloud3 '
  set -e
  cd /opt/specguard
  mkdir -p backups/p1
  stamp=$(date +%Y%m%d-%H%M%S)
  docker compose config > "backups/p1/compose-${stamp}.yaml"
  docker compose images > "backups/p1/images-${stamp}.txt"
  docker compose ps > "backups/p1/ps-before-${stamp}.txt"
  docker compose pull
  docker compose up -d --no-deps --scale app=2 app
  sleep 20
  docker compose ps
  curl -fsS http://127.0.0.1:8000/health
'
```

**产出文件**

- `cloud3:/opt/specguard/backups/p1/compose-<时间>.yaml`
- `cloud3:/opt/specguard/backups/p1/images-<时间>.txt`
- `cloud3:/opt/specguard/backups/p1/ps-before-<时间>.txt`
- 灰度实例运行记录

**验收命令与预期**

```bash
ssh cloud3 '
  cd /opt/specguard &&
  docker compose ps &&
  curl -fsS http://127.0.0.1:8000/health &&
  docker compose logs --since=10m --no-color | grep -Ei "traceback|fatal|panic" && exit 1 || exit 0
'
```

预期：健康检查返回成功；容器无重启循环；最近10分钟无`Traceback/FATAL/PANIC`。

**依赖**

- P1-D4-T1。
- 镜像已由CI构建并使用不可变版本标签。
- 大锤80批准生产窗口。

**时间**

`6h`

---

## P1-D14：全量验收与生产收口

### P1-D14-T1 7系统统一验收和P1关闭｜执行者：大锤80

**Shell命令**

```bash
cd /Users/maccc/projects/business-document-generator
.venv/bin/python tools/sdd_gate.py --root . --strict --require-test-mapping
.venv/bin/python -m pytest --cov=. --cov-fail-under=65 -q

cd /Users/maccc/projects/specguard
.venv/bin/python tools/sdd_gate.py --root . --strict
.venv/bin/python -m pytest --cov=. --cov-fail-under=85 -q

cd /opt/dh-enterprise-factory
python3 tools/sdd_gate.py --root . --strict --require-test-mapping
python3 -m pytest --cov=. --cov-fail-under=55 -q
bats tests/shell

ssh MacMini '
  cd /Users/mac/erp-project &&
  python3 tools/sdd_gate.py --root . --strict --require-test-mapping &&
  npm test -- --run --coverage &&
  npx prisma validate
'

cd /Users/maccc/daily_stock_analysis
python3 tools/sdd_gate.py --root . --strict --require-test-mapping
python3 -m pytest --cov=. --cov-fail-under=55 -q

cd /Users/maccc/Projects/ledger-quality-system
.venv/bin/python tools/sdd_gate.py --root . --strict --require-test-mapping
.venv/bin/python -m pytest --cov=. --cov-fail-under=50 -q

ssh cloud3 '
  cd /opt/specguard &&
  docker compose ps &&
  curl -fsS http://127.0.0.1:8000/health
'

cd /Users/maccc/projects/specguard
mkdir -p artifacts/p1/final
cursor artifacts/p1/final/P1-ACCEPTANCE.md
```

**产出文件**

- `artifacts/p1/final/P1-ACCEPTANCE.md`
- 6个开发仓库的最终测试和SDD报告
- cloud3生产健康检查记录
- 遗留问题清单及P2责任人

**验收命令与预期**

```bash
test -s /Users/maccc/projects/specguard/artifacts/p1/final/P1-ACCEPTANCE.md
ssh cloud3 'curl -fsS http://127.0.0.1:8000/health'
```

预期：

- business-api覆盖率≥`65%`
- specguard覆盖率≥`85%`
- dh-factory覆盖率≥`55%`
- erp-web覆盖率≥`50%`
- stock-api覆盖率≥`55%`
- ledger覆盖率≥`50%`
- 87份已知SDD全部通过统一规则或有带到期日的批准豁免
- cloud3生产健康检查通过

**依赖**

- P1-D1至P1-D13全部完成。
- 所有P0/P1阻断问题关闭或经大锤80书面批准延期。

**时间**

`8h`

---

# P2：自动化与跨系统治理（周级里程碑）

## P2-W1：中央质量台账

**负责人：cursor**

- 汇总6个开发仓库的SDD数量、通过率、覆盖率和CI状态。
- SpecGuard增加机器可读的统一JSON输出。
- 建立`artifacts/quality-dashboard.json`和静态质量看板。
- 验收：一次命令生成7系统质量快照，失败系统返回非零退出码。

## P2-W2：变更影响分析

**负责人：coder**

- 建立`SDD -> 模块 -> API -> 测试 -> 部署单元`关系。
- PR只执行受影响的SDD检查和测试集。
- 增加跨系统接口契约校验。
- 验收：修改一个API定义时，可列出受影响系统、SDD和测试。

## P2-W3：统一发布和回滚

**负责人：大锤80**

- 建立版本号、镜像标签、数据库迁移和回滚规范。
- cloud3实现不可变镜像发布。
- 每次生产发布自动保存compose配置、镜像摘要和健康记录。
- 验收：在预生产完成一次发布、健康检查和回滚演练。

## P2-W4：质量策略升级

**负责人：coder**

- 增加SDD过期、无Owner、无测试、接口不兼容等规则。
- 将覆盖率从全局阈值升级为全局阈值加变更代码覆盖率。
- 豁免必须包含审批人、原因和到期日。
- 验收：新增违规样例均能被CI准确阻断。

---

# P3：平台化与持续改进（周级里程碑）

## P3-W1：SpecGuard平台化

**负责人：coder**

- SpecGuard提供统一API、CLI和CI复用组件。
- 各仓库不再复制校验脚本，统一锁定SpecGuard版本。
- 支持GitHub Check结果和行级错误定位。
- 验收：6个开发仓库使用同一版本的SpecGuard执行门禁。

## P3-W2：生产观测与SLO

**负责人：大锤80**

- 定义可用性、错误率、延迟、任务成功率和发布失败率SLO。
- cloud3增加日志聚合、指标和告警。
- SDD验收条件与生产指标建立关联。
- 验收：能够从一次生产告警反查版本、SDD、提交和责任人。

## P3-W3：风险驱动测试

**负责人：cursor**

- 按业务风险为SDD分级。
- P0/P1需求必须具备单元、集成和回归测试。
- 高频变更模块增加属性测试、契约测试或端到端测试。
- 验收：测试资源根据风险自动分配，高风险变更不能仅靠覆盖率通过。

## P3-W4：治理闭环

**负责人：大锤80**

- 发布月度SDD质量报告。
- 清理过期SDD、过期豁免和无引用测试。
- 建立覆盖率下降、规则误报和生产逃逸缺陷复盘机制。
- 验收：形成下一周期P0-P3路线图，所有生产逃逸缺陷均能回写SDD和测试。