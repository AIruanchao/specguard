以下按 **10 个工作日、6 个系统并行推进**设计。默认使用 GitHub Actions；若实际为 GitLab/Jenkins，仅替换 CI 模板载体，任务和验收口径不变。

统一约定：

- 系统 ID：`business-api`、`specguard`、`dh-factory`、`erp-web`、`stock-api`、`ledger`
- 每个仓库必须提供：`make sdd-verify`、`make coverage`、`make ci`
- 统一清单：`sdd-manifest.yaml`
- 统一证据目录：`.sdd/evidence/`
- “零欠项”：清单内所有 P0 检查均有责任人、命令、结果和证据；不得出现 `TODO/TBD/SKIP/unknown`

---

## Day 1：盘点与口径冻结

### D1-T1 六系统现状扫描
**命令**
```bash
for repo in business-api specguard dh-factory erp-web stock-api ledger; do
  echo "=== $repo ==="
  git -C "$repo" rev-parse --show-toplevel
  find "$repo" -maxdepth 2 -type f \
    \( -name "pyproject.toml" -o -name "requirements.txt" \
       -o -name "package.json" -o -path "*/.github/workflows/*" \)
done
```
**产出**：`docs/sdd-p0/inventory.md`，记录语言、包管理器、测试命令、现有覆盖率、CI、负责人。  
**验收**：6/6 系统均有完整记录；未知项必须转为有负责人和截止日的阻塞项。  
**时间**：3h。

### D1-T2 冻结统一规范
**命令**
```bash
mkdir -p docs/sdd-p0 schemas templates
touch docs/sdd-p0/definition-of-done.md schemas/sdd-manifest.schema.json
```
**产出**：Manifest 字段、覆盖率口径、CI 阶段、零欠项定义及 P0 DoD。  
**验收**：技术负责人、测试负责人、6 系统 Owner 完成评审；规范版本标记为 `p0-v1`。  
**时间**：4h。

---

## Day 2：Manifest 模板与六系统落地

### D2-T1 实现 Manifest Schema 和校验器
**命令**
```bash
python -m pip install check-jsonschema pyyaml
check-jsonschema --schemafile schemas/sdd-manifest.schema.json \
  templates/sdd-manifest.example.yaml
```
**产出**：`schemas/sdd-manifest.schema.json`、示例 Manifest、`tools/validate_manifest.py`。  
**验收**：缺系统 ID、Owner、测试命令、覆盖率阈值或 CI 信息时校验必须失败。  
**时间**：4h。

### D2-T2 六系统创建 Manifest
**命令**
```bash
for repo in business-api specguard dh-factory erp-web stock-api ledger; do
  cp templates/sdd-manifest.example.yaml "$repo/sdd-manifest.yaml"
  mkdir -p "$repo/.sdd/evidence"
  python tools/validate_manifest.py "$repo/sdd-manifest.yaml"
done
```
**产出**：6 份 `sdd-manifest.yaml`。  
**验收**：6/6 Schema 校验通过；系统 ID 唯一；所有检查项有 Owner 和执行命令。  
**时间**：4h。

---

## Day 3：Python 第一批覆盖率基线

### D3-T1 商务 FastAPI、SpecGuard、DH 工厂接入覆盖率
**命令**
```bash
for repo in business-api specguard dh-factory; do
  cd "$repo"
  python -m pip install pytest pytest-cov
  pytest --cov=. --cov-report=term-missing \
    --cov-report=xml:.sdd/evidence/coverage.xml
  cd -
done
```
**产出**：3 个系统的 `coverage.xml`、缺失行报告、测试失败清单。  
**验收**：测试命令可重复执行；报告非空；不得用排除规则隐瞒业务代码。  
**时间**：5h。

### D3-T2 固化第一批基线
**命令**
```bash
python tools/update_coverage_baseline.py \
  business-api specguard dh-factory
git diff -- '*/sdd-manifest.yaml'
```
**产出**：Manifest 中的 `coverage.baseline`、`measured_at`、证据路径。  
**验收**：基线等于 CI 实测值；阈值不得低于基线，数值差异不超过 0.1 个百分点。  
**时间**：2h。

---

## Day 4：其余系统覆盖率基线

### D4-T1 股票 FastAPI、台账 Python 接入覆盖率
**命令**
```bash
for repo in stock-api ledger; do
  (cd "$repo" && python -m pip install pytest pytest-cov &&
   pytest --cov=. --cov-report=term-missing \
     --cov-report=xml:.sdd/evidence/coverage.xml)
done
```
**产出**：2 个 Python 系统的覆盖率报告和基线。  
**验收**：测试全通过；覆盖率 XML 可解析；Manifest 与实测值一致。  
**时间**：3h。

### D4-T2 ERP Next.js 接入覆盖率
**命令**
```bash
cd erp-web
npm ci
npm test -- --coverage --runInBand
npm run lint
npm run build
```
**产出**：`coverage/coverage-summary.json`、lint/build/test 结果及 ERP 基线。  
**验收**：覆盖率统计只包含应用源码；`lint`、测试、生产构建均通过。  
**时间**：4h。

---

## Day 5：统一 CI 模板

### D5-T1 编制 Python 与 Next.js CI 模板
**命令**
```bash
mkdir -p templates/github-actions
touch templates/github-actions/sdd-python.yml
touch templates/github-actions/sdd-nextjs.yml
actionlint templates/github-actions/*.yml
```
**产出**：两类可复用 CI 模板，包含 manifest、依赖、lint、test、coverage、artifact、零欠项阶段。  
**验收**：固定依赖安装方式；最小权限；支持缓存；失败时上传日志和覆盖率证据。  
**时间**：5h。

### D5-T2 统一本地入口
**命令**
```bash
for repo in business-api specguard dh-factory erp-web stock-api ledger; do
  make -C "$repo" sdd-verify
  make -C "$repo" coverage
  make -C "$repo" ci
done
```
**产出**：各仓库 `Makefile` 或等价任务文件。  
**验收**：3 个命令在 6 个系统中含义一致；本地和 CI 使用同一底层命令。  
**时间**：3h。

---

## Day 6：第一批 CI 接入

### D6-T1 商务 FastAPI、SpecGuard、DH 工厂启用 CI
**命令**
```bash
for repo in business-api specguard dh-factory; do
  cp templates/github-actions/sdd-python.yml \
    "$repo/.github/workflows/sdd-p0.yml"
  actionlint "$repo/.github/workflows/sdd-p0.yml"
  make -C "$repo" ci
done
```
**产出**：3 条仓库级 CI 流水线及运行证据。  
**验收**：PR 必跑；任一测试、Manifest、覆盖率或欠项检查失败时 CI 阻断。  
**时间**：5h。

### D6-T2 验证失败路径
**命令**
```bash
python tools/ci_negative_test.py \
  business-api specguard dh-factory \
  --cases invalid-manifest,coverage-regression,missing-evidence
```
**产出**：`.sdd/evidence/negative-tests.json`。  
**验收**：3 类故障在 3 个系统中全部被拦截，共 9/9 用例通过。  
**时间**：2h。

---

## Day 7：第二批 CI 接入

### D7-T1 ERP、股票、台账启用 CI
**命令**
```bash
cp templates/github-actions/sdd-nextjs.yml \
  erp-web/.github/workflows/sdd-p0.yml
for repo in stock-api ledger; do
  cp templates/github-actions/sdd-python.yml \
    "$repo/.github/workflows/sdd-p0.yml"
done
actionlint */.github/workflows/sdd-p0.yml
make -C erp-web ci
make -C stock-api ci
make -C ledger ci
```
**产出**：其余 3 条 CI 流水线及证据。  
**验收**：6/6 系统主分支和 PR 都启用必需检查；所有流水线通过。  
**时间**：5h。

### D7-T2 配置分支保护
**命令**
```bash
for repo in business-api specguard dh-factory erp-web stock-api ledger; do
  gh api -X PUT "repos/ORG/$repo/branches/main/protection" \
    --input config/branch-protection.json
done
```
**产出**：主分支保护配置快照。  
**验收**：禁止直接推送；必须通过 `sdd-p0`；不得由普通开发者绕过。  
**时间**：2h。

---

## Day 8：零欠项规则

### D8-T1 实现零欠项检查器
**命令**
```bash
python tools/check_zero_debt.py \
  --manifest-glob '*/sdd-manifest.yaml' \
  --evidence-glob '*/.sdd/evidence/**/*' \
  --deny 'TODO|TBD|SKIP|unknown'
```
**产出**：`tools/check_zero_debt.py`、`.sdd/evidence/debt-report.json`。  
**验收**：检查责任人、命令、状态、证据、豁免到期日；任一缺失返回非零退出码。  
**时间**：5h。

### D8-T2 接入全部流水线
**命令**
```bash
for repo in business-api specguard dh-factory erp-web stock-api ledger; do
  make -C "$repo" sdd-verify
done
```
**产出**：6 条流水线中的 `zero-debt` 必需 Job。  
**验收**：人为删除证据或加入 `TBD` 后 CI 必须失败；恢复后必须通过。  
**时间**：3h。

---

## Day 9：全量演练与收敛

### D9-T1 六系统干净环境演练
**命令**
```bash
rm -rf .sdd/run-p0 && mkdir -p .sdd/run-p0
for repo in business-api specguard dh-factory erp-web stock-api ledger; do
  make -C "$repo" clean ci 2>&1 | tee ".sdd/run-p0/$repo.log"
done
python tools/build_p0_report.py .sdd/run-p0
```
**产出**：六系统汇总报告、耗时、覆盖率、失败项、证据索引。  
**验收**：6/6 通过；报告内检查完成率 100%；P0 欠项数为 0。  
**时间**：5h。

### D9-T2 修复波动和基线偏差
**命令**
```bash
for n in 1 2 3; do
  for repo in business-api specguard dh-factory erp-web stock-api ledger; do
    make -C "$repo" ci
  done
done
```
**产出**：稳定性复测记录及修复提交。  
**验收**：连续 3 轮全部通过；无 flaky 测试；覆盖率波动不超过 0.1 个百分点。  
**时间**：3h。

---

## Day 10：冻结、验收和移交

### D10-T1 P0 最终验收
**命令**
```bash
python tools/validate_all.py \
  --schema schemas/sdd-manifest.schema.json \
  --require-systems business-api,specguard,dh-factory,erp-web,stock-api,ledger \
  --require-zero-debt
```
**产出**：`docs/sdd-p0/final-acceptance.md`、机器可读 `acceptance.json`。  
**验收**：Manifest 6/6、覆盖率基线 6/6、CI 6/6、分支保护 6/6、欠项 0。  
**时间**：3h。

### D10-T2 版本冻结与运维移交
**命令**
```bash
git tag -a sdd-p0-v1 -m "SDD P0 baseline"
git push origin sdd-p0-v1
sha256sum schemas/* templates/github-actions/* > docs/sdd-p0/checksums.txt
```
**产出**：`sdd-p0-v1` 标签、模板校验和、Owner 手册、故障处理说明。  
**验收**：任一系统可由新环境按文档在 30 分钟内完成验证；负责人签字齐全。  
**时间**：3h。

---

**P0 最终硬门槛**

| 指标 | 验收值 |
|---|---:|
| Manifest Schema 通过 | 6/6 |
| 覆盖率基线已固化 | 6/6 |
| PR 必需 CI 启用 | 6/6 |
| 分支保护启用 | 6/6 |
| 负向阻断用例 | 18/18 |
| 连续全量成功运行 | 3 次 |
| `TODO/TBD/SKIP/unknown` | 0 |
| 缺责任人、命令或证据项 | 0 |
| 未到期临时豁免 | 原则上 0；确需存在时不得计入 P0 完成 |