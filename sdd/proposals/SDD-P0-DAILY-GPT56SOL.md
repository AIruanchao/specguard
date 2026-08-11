# SDD 16周升级计划：P0（第1-4周）

> 总周期按投票共识固定为 **16周，不采用10周方案**。  
> P0占前4周，共20个工作日，目标是将SDD从 **12.6/24** 推进到 **16.9/24左右**，并为后续12周达到 **18+/24** 建立可执行基础。

## P0退出标准

| 目标 | 当前 | 第20日目标 | 分值 |
|---|---:|---:|---:|
| CI门禁 | 3/7 | 7/7 | +1.4 |
| 部署能力 | 骨架 | 7系统部署/验证/回滚清单完整 | +1.0 |
| Spec质量 | 骨架 | lint、追踪、变更检查、报告完整 | +0.8 |
| 运行记录 | 有欠项 | 连续10个工作日零欠项 | +0.8 |
| 覆盖率基线 | 3系统未测 | ERP、股票、台账建立基线 | +0.3 |

## 执行角色

| 执行者 | 职责 |
|---|---|
| 大锤80 | 决策、跨系统协调、门禁审批、异常关闭、最终验收 |
| cursor | CI、脚本、测试、部署文件的主要实施 |
| coder | 批量扫描、文档、报告、低风险测试补充 |

---

# 第1周：基线、统一标准与缺失CI

## Day 1：七系统P0基线冻结

**任务：建立统一盘点表、验收目录和P0基线报告。**

- **执行者**：大锤80（2h）+ coder（4h）
- **时间**：6h
- **依赖**：七系统访问权限；MacMini SSH别名可用；Docker只读权限可用

**Shell命令**

```bash
mkdir -p /Users/maccc/projects/specguard/ops/p0/{evidence,run-records,baselines}

cd /Users/maccc/projects/business-document-generator
git status --short
.venv/bin/python -m pytest --cov=. --cov-report=term-missing \
  | tee /Users/maccc/projects/specguard/ops/p0/baselines/business-tests.txt

cd /Users/maccc/projects/specguard
git status --short
.venv/bin/python -m pytest --cov=. --cov-report=term-missing \
  | tee ops/p0/baselines/specguard-tests.txt

cd /opt/dh-enterprise-factory
git status --short
python3 -m pytest --cov=. --cov-report=term-missing \
  | tee /Users/maccc/projects/specguard/ops/p0/baselines/dh-tests.txt

ssh MacMini 'cd /Users/mac/erp-project && git status --short && npm test -- --run' \
  | tee /Users/maccc/projects/specguard/ops/p0/baselines/erp-tests.txt

cd /Users/maccc/daily_stock_analysis
git status --short
python3 -m pytest --collect-only \
  | tee /Users/maccc/projects/specguard/ops/p0/baselines/stock-collect.txt

cd /Users/maccc/Projects/ledger-quality-system
git status --short
.venv311/bin/python3 -m pytest --collect-only \
  | tee /Users/maccc/projects/specguard/ops/p0/baselines/ledger-collect.txt

docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' \
  | tee /Users/maccc/projects/specguard/ops/p0/baselines/cloud3-containers.txt
```

**产出文件**

```text
/Users/maccc/projects/specguard/ops/p0/baselines/business-tests.txt
/Users/maccc/projects/specguard/ops/p0/baselines/specguard-tests.txt
/Users/maccc/projects/specguard/ops/p0/baselines/dh-tests.txt
/Users/maccc/projects/specguard/ops/p0/baselines/erp-tests.txt
/Users/maccc/projects/specguard/ops/p0/baselines/stock-collect.txt
/Users/maccc/projects/specguard/ops/p0/baselines/ledger-collect.txt
/Users/maccc/projects/specguard/ops/p0/baselines/cloud3-containers.txt
/Users/maccc/projects/specguard/ops/p0/P0-BASELINE.md
```

**验收命令**

```bash
test "$(find /Users/maccc/projects/specguard/ops/p0/baselines \
  -type f -size +0c | wc -l | tr -d ' ')" -ge 7
```

**预期**

```text
退出码为0；至少7份非空基线证据文件。
```

---

## Day 2：统一CI门禁契约

**任务：定义7系统共同的CI阶段、失败规则和证据格式。**

- **执行者**：cursor
- **时间**：6h
- **依赖**：Day 1基线

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p specs/quality schemas ops/p0/templates
touch specs/quality/ci-gate-policy.md
touch schemas/ci-evidence.schema.json
touch ops/p0/templates/run-record.md
touch ops/p0/templates/deployment-record.md
touch ops/p0/system-register.yaml
```

在文件中固化以下门禁：

```text
checkout/install -> lint -> unit-test -> coverage -> spec-check
-> build/package -> deployment-smoke -> evidence-upload
```

最低规则：

```text
所有测试必须退出码0
不得使用 continue-on-error 掩盖失败
覆盖率不得低于冻结基线
CI证据保留至少30天
主分支合并必须通过 required checks
cloud3只允许黑盒读取和健康检查，不允许容器内写入
```

**产出文件**

```text
/Users/maccc/projects/specguard/specs/quality/ci-gate-policy.md
/Users/maccc/projects/specguard/schemas/ci-evidence.schema.json
/Users/maccc/projects/specguard/ops/p0/templates/run-record.md
/Users/maccc/projects/specguard/ops/p0/templates/deployment-record.md
/Users/maccc/projects/specguard/ops/p0/system-register.yaml
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
test -s specs/quality/ci-gate-policy.md
test -s schemas/ci-evidence.schema.json
.venv/bin/python -m json.tool schemas/ci-evidence.schema.json >/dev/null
grep -q 'cloud3' ops/p0/system-register.yaml
```

**预期**

```text
全部退出码为0；JSON Schema可解析；系统登记表包含7个系统。
```

---

## Day 3：ERP覆盖率基线与CI

**任务：为ERP建立Vitest覆盖率基线并新增CI门禁。**

- **执行者**：cursor
- **时间**：8h
- **依赖**：MacMini仓库可写；Node依赖可安装

**Shell命令**

```bash
ssh MacMini '
  cd /Users/mac/erp-project &&
  npm ci &&
  npm install --save-dev @vitest/coverage-v8 &&
  mkdir -p .github/workflows scripts docs/quality &&
  npm test -- --run --coverage
'
```

新增 `.github/workflows/ci.yml`，固定执行：

```yaml
- run: npm ci
- run: npm test -- --run --coverage
- run: npm run build --if-present
```

如 `package.json` 尚无coverage脚本，增加：

```json
"test:coverage": "vitest run --coverage"
```

**产出文件**

```text
MacMini:/Users/mac/erp-project/.github/workflows/ci.yml
MacMini:/Users/mac/erp-project/package.json
MacMini:/Users/mac/erp-project/docs/quality/coverage-baseline.md
MacMini:/Users/mac/erp-project/coverage/coverage-summary.json
```

**验收命令**

```bash
ssh MacMini '
  cd /Users/mac/erp-project &&
  npm test -- --run --coverage &&
  test -s coverage/coverage-summary.json &&
  git diff --check
'
```

**预期**

```text
Vitest通过；coverage-summary.json非空；CI配置包含测试和构建步骤。
```

---

## Day 4：股票系统覆盖率基线与CI

**任务：识别股票系统测试入口，建立pytest覆盖率基线和CI。**

- **执行者**：cursor
- **时间**：8h
- **依赖**：Day 1收集结果；依赖可安装

**Shell命令**

```bash
cd /Users/maccc/daily_stock_analysis
mkdir -p .github/workflows docs/quality
python3 -m pip install pytest pytest-cov
python3 -m pytest --collect-only
python3 -m pytest --cov=. --cov-report=term-missing \
  --cov-report=json:coverage.json
```

新增 `.github/workflows/ci.yml`，使用仓库实际依赖文件：

```bash
cd /Users/maccc/daily_stock_analysis
test -f requirements.txt && python3 -m pip install -r requirements.txt
test -f pyproject.toml && python3 -m pip install -e .
```

CI核心命令：

```yaml
- run: python3 -m pytest --cov=. --cov-report=term-missing --cov-report=json:coverage.json
```

**产出文件**

```text
/Users/maccc/daily_stock_analysis/.github/workflows/ci.yml
/Users/maccc/daily_stock_analysis/coverage.json
/Users/maccc/daily_stock_analysis/docs/quality/coverage-baseline.md
```

**验收命令**

```bash
cd /Users/maccc/daily_stock_analysis
python3 -m pytest --cov=. --cov-report=json:coverage.json
python3 -m json.tool coverage.json >/dev/null
git diff --check
```

**预期**

```text
测试退出码为0；coverage.json可解析；覆盖率数值被记录为冻结基线。
```

---

## Day 5：台账系统覆盖率基线与CI

**任务：为台账系统建立Python 3.11测试、覆盖率和CI门禁。**

- **执行者**：cursor
- **时间**：8h
- **依赖**：`.venv311`可用；仓库依赖完整

**Shell命令**

```bash
cd /Users/maccc/Projects/ledger-quality-system
mkdir -p .github/workflows docs/quality
.venv311/bin/python3 -m pip install pytest pytest-cov
.venv311/bin/python3 -m pytest --collect-only
.venv311/bin/python3 -m pytest --cov=. --cov-report=term-missing \
  --cov-report=json:coverage.json
```

CI使用Python 3.11：

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"
- run: python -m pytest --cov=. --cov-report=json:coverage.json
```

**产出文件**

```text
/Users/maccc/Projects/ledger-quality-system/.github/workflows/ci.yml
/Users/maccc/Projects/ledger-quality-system/coverage.json
/Users/maccc/Projects/ledger-quality-system/docs/quality/coverage-baseline.md
```

**验收命令**

```bash
cd /Users/maccc/Projects/ledger-quality-system
.venv311/bin/python3 -m pytest --cov=. \
  --cov-report=json:coverage.json
.venv311/bin/python3 -m json.tool coverage.json >/dev/null
git diff --check
```

**预期**

```text
测试通过；覆盖率JSON有效；ERP、股票、台账三个未测系统均已有基线。
```

---

# 第2周：CI补齐与部署能力

## Day 6：商务FastAPI门禁加固

**任务：把现有45%覆盖率升级为不可回退门禁，并增加应用导入检查。**

- **执行者**：cursor
- **时间**：6h
- **依赖**：现有CI可运行

**Shell命令**

```bash
cd /Users/maccc/projects/business-document-generator
mkdir -p scripts docs/quality
.venv/bin/python -m pytest --cov=. --cov-fail-under=45 \
  --cov-report=xml:coverage.xml
.venv/bin/python -m compileall -q .
```

CI增加：

```yaml
- run: .venv/bin/python -m compileall -q .
- run: .venv/bin/python -m pytest --cov=. --cov-fail-under=45 --cov-report=xml
```

**产出文件**

```text
/Users/maccc/projects/business-document-generator/.github/workflows/ci.yml
/Users/maccc/projects/business-document-generator/docs/quality/coverage-baseline.md
/Users/maccc/projects/business-document-generator/coverage.xml
```

**验收命令**

```bash
cd /Users/maccc/projects/business-document-generator
.venv/bin/python -m pytest --cov=. --cov-fail-under=45
.venv/bin/python -m compileall -q .
git diff --check
```

**预期**

```text
覆盖率不低于45%；应用代码可编译；降低覆盖率会导致CI失败。
```

---

## Day 7：SpecGuard门禁加固

**任务：冻结81%覆盖率并将Spec质量检查接入自身CI。**

- **执行者**：cursor
- **时间**：7h
- **依赖**：Day 2质量契约

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p scripts reports/spec-quality
.venv/bin/python -m pytest --cov=. --cov-fail-under=81 \
  --cov-report=xml:coverage.xml
.venv/bin/python -m compileall -q .
```

CI核心步骤：

```yaml
- run: .venv/bin/python -m pytest --cov=. --cov-fail-under=81 --cov-report=xml
- run: .venv/bin/python scripts/check_specs.py
- run: .venv/bin/python scripts/check_traceability.py
```

**产出文件**

```text
/Users/maccc/projects/specguard/.github/workflows/ci.yml
/Users/maccc/projects/specguard/scripts/check_specs.py
/Users/maccc/projects/specguard/scripts/check_traceability.py
/Users/maccc/projects/specguard/reports/spec-quality/
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python -m pytest --cov=. --cov-fail-under=81
.venv/bin/python scripts/check_specs.py
.venv/bin/python scripts/check_traceability.py
```

**预期**

```text
三条命令均返回0；无效Spec或缺失追踪关系会返回非0。
```

---

## Day 8：DH工厂门禁加固

**任务：冻结32%覆盖率，补齐构建和部署清单验证。**

- **执行者**：cursor
- **时间**：7h
- **依赖**：`/opt/dh-enterprise-factory`可写

**Shell命令**

```bash
cd /opt/dh-enterprise-factory
mkdir -p scripts docs/quality deploy
python3 -m pytest --cov=. --cov-fail-under=32 \
  --cov-report=xml:coverage.xml
python3 -m compileall -q .
```

CI核心步骤：

```yaml
- run: python3 -m compileall -q .
- run: python3 -m pytest --cov=. --cov-fail-under=32 --cov-report=xml
- run: python3 scripts/validate_deployment.py
```

**产出文件**

```text
/opt/dh-enterprise-factory/.github/workflows/ci.yml
/opt/dh-enterprise-factory/scripts/validate_deployment.py
/opt/dh-enterprise-factory/docs/quality/coverage-baseline.md
/opt/dh-enterprise-factory/deploy/deployment-manifest.yaml
```

**验收命令**

```bash
cd /opt/dh-enterprise-factory
python3 -m pytest --cov=. --cov-fail-under=32
python3 scripts/validate_deployment.py
git diff --check
```

**预期**

```text
覆盖率不低于32%；部署清单字段完整；CI失败不可被忽略。
```

---

## Day 9：cloud3只读外部CI门禁

**任务：不修改cloud3容器，通过SpecGuard建立外部黑盒门禁。**

- **执行者**：cursor（6h）+ 大锤80（2h）
- **时间**：8h
- **依赖**：Docker只读权限；配置self-hosted runner标签 `cloud3-readonly`

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p ops/cloud3 .github/workflows reports/cloud3
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
docker inspect "$(docker ps -q | head -n 1)" >/dev/null
```

新增只读检查脚本，限定命令：

```text
docker ps
docker inspect
docker logs --tail
HTTP GET健康检查
禁止docker exec写操作
禁止docker cp写入
禁止docker restart/stop/rm
```

工作流使用：

```yaml
runs-on: [self-hosted, cloud3-readonly]
```

**产出文件**

```text
/Users/maccc/projects/specguard/ops/cloud3/readonly-smoke.sh
/Users/maccc/projects/specguard/ops/cloud3/cloud3-services.yaml
/Users/maccc/projects/specguard/.github/workflows/cloud3-readonly-gate.yml
/Users/maccc/projects/specguard/reports/cloud3/
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
bash -n ops/cloud3/readonly-smoke.sh
bash ops/cloud3/readonly-smoke.sh
! grep -En 'docker +(exec|cp|restart|stop|rm|kill)' \
  ops/cloud3/readonly-smoke.sh
```

**预期**

```text
只读冒烟检查返回0；脚本不包含容器写入或生命周期变更命令。
```

---

## Day 10：七系统CI总验收

**任务：统一运行本地/远程门禁，生成7/7状态报告。**

- **执行者**：大锤80（3h）+ coder（5h）
- **时间**：8h
- **依赖**：Day 3-9完成；各CI已触发至少一次

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p reports/p0-ci

cd /Users/maccc/projects/business-document-generator
.venv/bin/python -m pytest --cov=. --cov-fail-under=45

cd /Users/maccc/projects/specguard
.venv/bin/python -m pytest --cov=. --cov-fail-under=81

cd /opt/dh-enterprise-factory
python3 -m pytest --cov=. --cov-fail-under=32

ssh MacMini \
  'cd /Users/mac/erp-project && npm ci && npm test -- --run --coverage'

cd /Users/maccc/daily_stock_analysis
python3 -m pytest --cov=. --cov-report=json:coverage.json

cd /Users/maccc/Projects/ledger-quality-system
.venv311/bin/python3 -m pytest --cov=. \
  --cov-report=json:coverage.json

cd /Users/maccc/projects/specguard
bash ops/cloud3/readonly-smoke.sh
```

**产出文件**

```text
/Users/maccc/projects/specguard/reports/p0-ci/7-system-ci-status.md
/Users/maccc/projects/specguard/reports/p0-ci/7-system-ci-evidence.json
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python scripts/validate_ci_evidence.py \
  reports/p0-ci/7-system-ci-evidence.json
```

**预期**

```text
business=PASS
specguard=PASS
dh-factory=PASS
erp=PASS
stock=PASS
ledger=PASS
cloud3=PASS
总计：7/7
```

---

# 第3周：部署骨架完整化与Spec质量

## Day 11：统一部署契约

**任务：定义部署前置检查、部署、冒烟、回滚和证据标准。**

- **执行者**：大锤80（2h）+ cursor（5h）
- **时间**：7h
- **依赖**：7/7 CI通过

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p specs/deployment schemas deploy/templates
touch specs/deployment/deployment-standard.md
touch schemas/deployment-manifest.schema.json
touch deploy/templates/preflight.sh
touch deploy/templates/smoke.sh
touch deploy/templates/rollback.md
chmod +x deploy/templates/preflight.sh deploy/templates/smoke.sh
```

**产出文件**

```text
/Users/maccc/projects/specguard/specs/deployment/deployment-standard.md
/Users/maccc/projects/specguard/schemas/deployment-manifest.schema.json
/Users/maccc/projects/specguard/deploy/templates/preflight.sh
/Users/maccc/projects/specguard/deploy/templates/smoke.sh
/Users/maccc/projects/specguard/deploy/templates/rollback.md
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
bash -n deploy/templates/preflight.sh
bash -n deploy/templates/smoke.sh
.venv/bin/python -m json.tool \
  schemas/deployment-manifest.schema.json >/dev/null
```

**预期**

```text
脚本语法通过；Schema有效；标准明确部署、冒烟、回滚、证据四阶段。
```

---

## Day 12：商务与DH部署完整化

**任务：为商务FastAPI和DH工厂补齐部署清单、健康检查和回滚说明。**

- **执行者**：cursor
- **时间**：8h
- **依赖**：Day 11部署契约

**Shell命令**

```bash
cd /Users/maccc/projects/business-document-generator
mkdir -p deploy
touch deploy/manifest.yaml deploy/preflight.sh deploy/smoke.sh deploy/rollback.md
chmod +x deploy/preflight.sh deploy/smoke.sh

cd /opt/dh-enterprise-factory
mkdir -p deploy
touch deploy/manifest.yaml deploy/preflight.sh deploy/smoke.sh deploy/rollback.md
chmod +x deploy/preflight.sh deploy/smoke.sh
```

脚本至少检查：

```text
Python版本
依赖可导入
配置项存在但不输出密钥
端口可绑定
健康检查返回2xx
回滚版本和命令明确
```

**产出文件**

```text
/Users/maccc/projects/business-document-generator/deploy/*
/opt/dh-enterprise-factory/deploy/*
```

**验收命令**

```bash
cd /Users/maccc/projects/business-document-generator
bash -n deploy/preflight.sh
bash -n deploy/smoke.sh
test -s deploy/manifest.yaml
test -s deploy/rollback.md

cd /opt/dh-enterprise-factory
bash -n deploy/preflight.sh
bash -n deploy/smoke.sh
test -s deploy/manifest.yaml
test -s deploy/rollback.md
```

**预期**

```text
两个系统均具备可执行前置检查、冒烟检查、部署清单和明确回滚步骤。
```

---

## Day 13：ERP、股票、台账部署完整化

**任务：为三个新增CI系统补齐部署和回滚材料。**

- **执行者**：cursor
- **时间**：8h
- **依赖**：三个系统CI通过

**Shell命令**

```bash
ssh MacMini '
  cd /Users/mac/erp-project &&
  mkdir -p deploy &&
  touch deploy/manifest.yaml deploy/preflight.sh deploy/smoke.sh deploy/rollback.md &&
  chmod +x deploy/preflight.sh deploy/smoke.sh
'

cd /Users/maccc/daily_stock_analysis
mkdir -p deploy
touch deploy/manifest.yaml deploy/preflight.sh deploy/smoke.sh deploy/rollback.md
chmod +x deploy/preflight.sh deploy/smoke.sh

cd /Users/maccc/Projects/ledger-quality-system
mkdir -p deploy
touch deploy/manifest.yaml deploy/preflight.sh deploy/smoke.sh deploy/rollback.md
chmod +x deploy/preflight.sh deploy/smoke.sh
```

**产出文件**

```text
MacMini:/Users/mac/erp-project/deploy/*
/Users/maccc/daily_stock_analysis/deploy/*
/Users/maccc/Projects/ledger-quality-system/deploy/*
```

**验收命令**

```bash
ssh MacMini '
  cd /Users/mac/erp-project &&
  bash -n deploy/preflight.sh &&
  bash -n deploy/smoke.sh &&
  test -s deploy/manifest.yaml &&
  test -s deploy/rollback.md
'

for repo in \
  /Users/maccc/daily_stock_analysis \
  /Users/maccc/Projects/ledger-quality-system
do
  cd "$repo"
  bash -n deploy/preflight.sh
  bash -n deploy/smoke.sh
  test -s deploy/manifest.yaml
  test -s deploy/rollback.md
done
```

**预期**

```text
ERP、股票、台账全部通过部署材料完整性检查。
```

---

## Day 14：Spec质量完整化

**任务：实现Spec结构、追踪关系、变更影响和未决项检查。**

- **执行者**：cursor（6h）+ coder（2h）
- **时间**：8h
- **依赖**：Day 2、Day 7

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p specs/templates reports/spec-quality
touch specs/templates/spec-template.md
touch schemas/spec.schema.json
touch scripts/check_spec_structure.py
touch scripts/check_spec_traceability.py
touch scripts/check_spec_change_impact.py
touch scripts/check_open_items.py
```

统一检查：

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python scripts/check_spec_structure.py
.venv/bin/python scripts/check_spec_traceability.py
.venv/bin/python scripts/check_spec_change_impact.py
.venv/bin/python scripts/check_open_items.py
```

**产出文件**

```text
/Users/maccc/projects/specguard/specs/templates/spec-template.md
/Users/maccc/projects/specguard/schemas/spec.schema.json
/Users/maccc/projects/specguard/scripts/check_spec_structure.py
/Users/maccc/projects/specguard/scripts/check_spec_traceability.py
/Users/maccc/projects/specguard/scripts/check_spec_change_impact.py
/Users/maccc/projects/specguard/scripts/check_open_items.py
/Users/maccc/projects/specguard/reports/spec-quality/spec-quality.json
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
for check in \
  check_spec_structure.py \
  check_spec_traceability.py \
  check_spec_change_impact.py \
  check_open_items.py
do
  .venv/bin/python "scripts/$check"
done
```

**预期**

```text
四项检查全部通过；缺失owner、验收标准、追踪ID或影响分析时返回非0。
```

---

## Day 15：七系统部署与Spec联合验收

**任务：生成完整部署矩阵，确认7系统都有部署或只读验证路径。**

- **执行者**：大锤80（3h）+ coder（4h）
- **时间**：7h
- **依赖**：Day 11-14

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p reports/deployment
touch reports/deployment/7-system-deployment-matrix.md
touch reports/deployment/7-system-deployment-evidence.json

.venv/bin/python scripts/check_spec_structure.py
.venv/bin/python scripts/check_spec_traceability.py
.venv/bin/python scripts/validate_deployment_matrix.py \
  reports/deployment/7-system-deployment-evidence.json
```

cloud3在矩阵中定义为：

```text
deployment_mode: external-readonly
preflight: docker inspect
smoke: HTTP GET / health
rollback: N/A，由cloud3所有者执行
write_access: forbidden
```

**产出文件**

```text
/Users/maccc/projects/specguard/reports/deployment/7-system-deployment-matrix.md
/Users/maccc/projects/specguard/reports/deployment/7-system-deployment-evidence.json
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python scripts/validate_deployment_matrix.py \
  reports/deployment/7-system-deployment-evidence.json
```

**预期**

```text
7/7系统均有preflight、deploy/read-only、smoke、rollback/owner、evidence定义。
```

---

# 第4周：零欠项运行与P0退出验收

## Day 16：运行记录机制上线

**任务：建立每日运行记录、欠项判定和自动汇总。**

- **执行者**：cursor
- **时间**：7h
- **依赖**：CI和部署矩阵完成

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p ops/p0/run-records scripts reports/operations
touch scripts/create_daily_run_record.py
touch scripts/validate_run_records.py
touch scripts/summarize_run_records.py

.venv/bin/python scripts/create_daily_run_record.py \
  --date "$(date +%F)" \
  --output "ops/p0/run-records/$(date +%F).yaml"
```

每日记录字段：

```text
date
system
ci_status
deployment_status
incident_count
open_item_count
owner
evidence
closed_at
```

**产出文件**

```text
/Users/maccc/projects/specguard/scripts/create_daily_run_record.py
/Users/maccc/projects/specguard/scripts/validate_run_records.py
/Users/maccc/projects/specguard/scripts/summarize_run_records.py
/Users/maccc/projects/specguard/ops/p0/run-records/YYYY-MM-DD.yaml
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python scripts/validate_run_records.py \
  ops/p0/run-records
```

**预期**

```text
当天7个系统记录完整；open_item_count全部为0；缺字段或未关闭项会失败。
```

---

## Day 17：运行日检与故障演练

**任务：执行一次CI失败和回滚桌面演练，所有演练项当日关闭。**

- **执行者**：大锤80（3h）+ cursor（4h）
- **时间**：7h
- **依赖**：Day 16记录机制

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p ops/p0/drills
touch ops/p0/drills/ci-failure-drill.md
touch ops/p0/drills/deployment-rollback-drill.md

.venv/bin/python scripts/create_daily_run_record.py \
  --date "$(date +%F)" \
  --output "ops/p0/run-records/$(date +%F).yaml"

.venv/bin/python scripts/validate_run_records.py \
  ops/p0/run-records
```

演练范围：

```text
覆盖率低于基线时CI必须失败
部署冒烟失败时不得宣布成功
回滚责任人和恢复时限明确
演练产生的问题必须当日关闭
```

**产出文件**

```text
/Users/maccc/projects/specguard/ops/p0/drills/ci-failure-drill.md
/Users/maccc/projects/specguard/ops/p0/drills/deployment-rollback-drill.md
/Users/maccc/projects/specguard/ops/p0/run-records/YYYY-MM-DD.yaml
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
grep -q 'result: PASS' ops/p0/drills/ci-failure-drill.md
grep -q 'result: PASS' ops/p0/drills/deployment-rollback-drill.md
.venv/bin/python scripts/check_open_items.py
```

**预期**

```text
两项演练均PASS；未关闭项为0。
```

---

## Day 18：全链路回归

**任务：重跑七系统测试、覆盖率、Spec和部署验证。**

- **执行者**：cursor（5h）+ coder（3h）
- **时间**：8h
- **依赖**：所有实施工作完成

**Shell命令**

```bash
cd /Users/maccc/projects/business-document-generator
.venv/bin/python -m pytest --cov=. --cov-fail-under=45

cd /Users/maccc/projects/specguard
.venv/bin/python -m pytest --cov=. --cov-fail-under=81

cd /opt/dh-enterprise-factory
python3 -m pytest --cov=. --cov-fail-under=32

ssh MacMini \
  'cd /Users/mac/erp-project && npm ci && npm test -- --run --coverage'

cd /Users/maccc/daily_stock_analysis
python3 -m pytest --cov=. --cov-report=json:coverage.json

cd /Users/maccc/Projects/ledger-quality-system
.venv311/bin/python3 -m pytest --cov=. \
  --cov-report=json:coverage.json

cd /Users/maccc/projects/specguard
bash ops/cloud3/readonly-smoke.sh
.venv/bin/python scripts/check_spec_structure.py
.venv/bin/python scripts/check_spec_traceability.py
.venv/bin/python scripts/validate_deployment_matrix.py \
  reports/deployment/7-system-deployment-evidence.json
```

**产出文件**

```text
/Users/maccc/projects/specguard/reports/p0-regression/day18-regression.md
/Users/maccc/projects/specguard/reports/p0-regression/day18-evidence.json
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python scripts/validate_ci_evidence.py \
  reports/p0-regression/day18-evidence.json
.venv/bin/python scripts/check_open_items.py
```

**预期**

```text
七系统全部PASS；部署矩阵PASS；Spec检查PASS；欠项为0。
```

---

## Day 19：P0预验收与缺口清零

**任务：按五个P0目标逐项评分，只允许关闭问题，不新增范围。**

- **执行者**：大锤80（4h）+ cursor（3h）
- **时间**：7h
- **依赖**：Day 18全链路通过

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p reports/p0-acceptance
touch reports/p0-acceptance/P0-PRE-ACCEPTANCE.md
touch reports/p0-acceptance/P0-SCORE.json

.venv/bin/python scripts/validate_ci_evidence.py \
  reports/p0-ci/7-system-ci-evidence.json

.venv/bin/python scripts/validate_deployment_matrix.py \
  reports/deployment/7-system-deployment-evidence.json

.venv/bin/python scripts/check_spec_structure.py
.venv/bin/python scripts/check_spec_traceability.py
.venv/bin/python scripts/check_open_items.py
.venv/bin/python scripts/validate_run_records.py ops/p0/run-records
```

**产出文件**

```text
/Users/maccc/projects/specguard/reports/p0-acceptance/P0-PRE-ACCEPTANCE.md
/Users/maccc/projects/specguard/reports/p0-acceptance/P0-SCORE.json
/Users/maccc/projects/specguard/reports/p0-acceptance/P0-GAPS.md
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard
.venv/bin/python - <<'PY'
import json
from pathlib import Path

score = json.loads(
    Path("reports/p0-acceptance/P0-SCORE.json").read_text()
)
assert score["ci_gate"] == 7
assert score["deployment_complete"] is True
assert score["spec_quality_complete"] is True
assert score["open_items"] == 0
assert score["coverage_baselines"] >= 3
print("P0 PRE-ACCEPTANCE: PASS")
PY
```

**预期**

```text
P0 PRE-ACCEPTANCE: PASS
P0-GAPS.md中不存在P0级未关闭项。
```

---

## Day 20：P0正式验收与16周基线封版

**任务：完成P0签收，冻结证据，并发布第5-16周输入基线。**

- **执行者**：大锤80（5h）+ coder（3h）
- **时间**：8h
- **依赖**：Day 19预验收通过；所有P0欠项清零

**Shell命令**

```bash
cd /Users/maccc/projects/specguard
mkdir -p reports/p0-final releases/p0
touch reports/p0-final/P0-FINAL-ACCEPTANCE.md
touch reports/p0-final/P0-METRICS.json
touch reports/p0-final/WEEK-5-16-INPUT.md

.venv/bin/python scripts/summarize_run_records.py \
  --input ops/p0/run-records \
  --output reports/p0-final/run-record-summary.json

.venv/bin/python scripts/validate_ci_evidence.py \
  reports/p0-ci/7-system-ci-evidence.json

.venv/bin/python scripts/validate_deployment_matrix.py \
  reports/deployment/7-system-deployment-evidence.json

.venv/bin/python scripts/check_open_items.py
.venv/bin/python scripts/validate_run_records.py ops/p0/run-records

tar -czf releases/p0/p0-evidence-$(date +%F).tar.gz \
  reports/p0-ci \
  reports/deployment \
  reports/spec-quality \
  reports/operations \
  reports/p0-acceptance \
  reports/p0-final \
  ops/p0/run-records
```

**产出文件**

```text
/Users/maccc/projects/specguard/reports/p0-final/P0-FINAL-ACCEPTANCE.md
/Users/maccc/projects/specguard/reports/p0-final/P0-METRICS.json
/Users/maccc/projects/specguard/reports/p0-final/WEEK-5-16-INPUT.md
/Users/maccc/projects/specguard/reports/p0-final/run-record-summary.json
/Users/maccc/projects/specguard/releases/p0/p0-evidence-YYYY-MM-DD.tar.gz
```

**验收命令**

```bash
cd /Users/maccc/projects/specguard

test -s reports/p0-final/P0-FINAL-ACCEPTANCE.md
test -s reports/p0-final/P0-METRICS.json
test -s reports/p0-final/WEEK-5-16-INPUT.md
test -s "releases/p0/p0-evidence-$(date +%F).tar.gz"

.venv/bin/python - <<'PY'
import json
from pathlib import Path

m = json.loads(Path("reports/p0-final/P0-METRICS.json").read_text())
assert m["ci"]["passed"] == 7
assert m["ci"]["total"] == 7
assert m["deployment"]["complete"] is True
assert m["spec_quality"]["complete"] is True
assert m["operations"]["open_items"] == 0
assert m["coverage"]["new_baselines"] == 3
assert m["sdd"]["program_weeks"] == 16
assert m["sdd"]["target_score"] >= 18
print("P0 FINAL ACCEPTANCE: PASS")
PY
```

**预期**

```text
P0 FINAL ACCEPTANCE: PASS

CI门禁：7/7
部署能力：完整
Spec质量：完整
运行记录：零欠项
新增覆盖率基线：3/3
P0增分：+4.3
SDD阶段分：约16.9/24
总周期：16周
最终目标：18+/24
```

# 每日固定收口动作

从Day 1开始，每个工作日下班前执行；Day 11-20必须形成连续10个工作日零欠项记录：

```bash
cd /Users/maccc/projects/specguard

.venv/bin/python scripts/create_daily_run_record.py \
  --date "$(date +%F)" \
  --output "ops/p0/run-records/$(date +%F).yaml"

.venv/bin/python scripts/check_open_items.py
.venv/bin/python scripts/validate_run_records.py ops/p0/run-records
```

预期：

```text
当日7系统状态都有证据链接。
所有失败项都有owner、截止时间和关闭记录。
每日结束时open_item_count=0。
连续10个工作日不存在跨日P0欠项。
```

# P0后12周边界

| 阶段 | 周期 | 重点 |
|---|---:|---|
| P0 | 第1-4周 | CI 7/7、部署完整、Spec完整、零欠项、覆盖率基线 |
| P1 | 第5-8周 | 核心路径覆盖率提升、契约测试、发布自动化 |
| P2 | 第9-12周 | 可观测性、故障恢复、性能与安全门禁 |
| P3 | 第13-16周 | 跨系统追踪、审计封版、SDD 18+/24正式验收 |