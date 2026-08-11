# SDD 20个工作日冲刺方案（17.4 → 20.6/24）

## 目标与验收口径

- **总目标**：20个工作日后达到 **20.6/24**，至少确保 **20+/24**。
- **覆盖率 +1.2**：六个可编辑系统按有效代码行加权总覆盖率 `>=60%`；每个系统不得低于 `50%`。商务与 SpecGuard 保持现状，重点提升 DH、ERP、股票、台账。cloud3 只读，纳入基线和证据归档，不在容器内写文件。
- **Spec质量 +1.0**：股票、台账 Spec 从 draft 升为 confirmed；需求、验收条件、测试用例三者可追踪，映射覆盖率 `100%`，人工核验签字。
- **AI修复 +0.6**：建立冻结的100样本评测集，一次性盲测成功率 `>=50%`；不得用评测集反复调参。
- **逆向引擎 +0.4**：建立经人工标注的数据集，冻结测试集；输出 precision、recall、F1、误报和漏报清单。
- **防刷分规则**：不得通过扩大 omit、删除失败测试、降低断言强度或只测 getter/setter 提升指标。

## 第1周：基线、口径和高价值测试

### Day 1：冻结全系统基线
- **具体命令**：
  ```bash
  cd /Users/maccc/projects/business-document-generator && .venv/bin/python -m pytest --cov=. --cov-report=json:coverage.json
  cd /Users/maccc/projects/specguard && .venv/bin/python -m pytest --cov=. --cov-report=json:coverage.json
  cd /opt/dh-enterprise-factory && python3 -m pytest --cov=. --cov-report=json:coverage.json
  ssh mac@10.31.1.177 'cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH npm test -- --coverage'
  cd /Users/maccc/daily_stock_analysis && python3 -m pytest --cov=. --cov-report=json:coverage.json
  cd /Users/maccc/Projects/ledger-quality-system && .venv311/bin/python3 -m pytest --cov=. --cov-report=json:coverage.json
  docker ps --format '{{.ID}} {{.Names}} {{.Image}}' > /tmp/cloud3-containers.txt
  curl -fsS http://127.0.0.1:9100/openapi.json -o /tmp/ai-fix-openapi.json
  curl -fsS http://127.0.0.1:9201/openapi.json -o /tmp/review-agent-openapi.json
  ```
- **产出**：`SDD-baseline-YYYYMMDD.md`、六套 coverage JSON/ERP coverage summary、cloud3只读证据、自动化API清单。
- **验收**：报告记录代码提交 SHA、测试数、覆盖率分子/分母、失败项；历史数据与新基线差异均有解释。
- **依赖**：MacMini SSH、Docker读取权限、`pytest-cov` 已安装；缺失时仅安装到对应虚拟环境并记录。
- **时间**：8小时。
- **执行者**：coder执行采集；大锤80确认统计口径。

### Day 2：建立覆盖率缺口清单和测试队列
- **具体命令**：
  ```bash
  cd /opt/dh-enterprise-factory && python3 -m coverage report -m --sort=cover
  ssh mac@10.31.1.177 "cd /Users/mac/erp-project && find coverage -name 'coverage-summary.json' -o -name 'lcov.info'"
  cd /Users/maccc/daily_stock_analysis && python3 -m coverage report -m --sort=cover
  cd /Users/maccc/Projects/ledger-quality-system && .venv311/bin/python3 -m coverage report -m --sort=cover
  rg -n "TODO|pass$|NotImplemented|except Exception|if .*error|raise " /opt/dh-enterprise-factory /Users/maccc/daily_stock_analysis /Users/maccc/Projects/ledger-quality-system
  ```
- **产出**：按“未覆盖行数 × 业务风险”排序的测试 backlog，分别列出 P0/P1 模块、预计新增用例和目标覆盖率。
- **验收**：DH、ERP、股票、台账各至少选出10个高价值路径；所有条目关联文件、分支和测试类型。
- **依赖**：Day 1基线。
- **时间**：6小时。
- **执行者**：大锤80定优先级；coder生成清单。

### Day 3：DH核心成功路径测试
- **具体命令**：
  ```bash
  cd /opt/dh-enterprise-factory
  rg --files | rg '(^|/)(api|service|core|factory|workflow).*\.py$'
  python3 -m pytest tests -q --cov=. --cov-report=term-missing --cov-report=json:coverage.json
  ```
- **产出**：为订单/任务创建、工厂流程、状态转换等最高风险成功路径新增单元及服务层测试。
- **验收**：新增 `>=25` 个有效测试；DH全量测试通过；DH覆盖率从44%提升到 `>=49%`。
- **依赖**：Day 2 DH P0清单；测试不得依赖外网或生产数据。
- **时间**：8小时。
- **执行者**：cursor编写测试；大锤80审查断言质量。

### Day 4：DH异常、边界和回归测试
- **具体命令**：
  ```bash
  cd /opt/dh-enterprise-factory
  python3 -m pytest tests -q --maxfail=1
  python3 -m pytest tests -q --cov=. --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
  ```
- **产出**：权限拒绝、非法状态、空输入、重复提交、依赖超时和回滚路径测试。
- **验收**：新增 `>=25` 个测试；分支覆盖率有记录；DH总覆盖率 `>=54%`，无新增 flaky 测试。
- **依赖**：Day 3测试夹具可复用。
- **时间**：8小时。
- **执行者**：cursor实现；coder连续运行3次检测稳定性。

### Day 5：ERP覆盖率基线解析与首批测试
- **具体命令**：
  ```bash
  ssh mac@10.31.1.177 'cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH node -p "JSON.stringify(require(\"./package.json\").scripts,null,2)"'
  ssh mac@10.31.1.177 'cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH npm test -- --coverage --runInBand'
  ssh mac@10.31.1.177 'cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH find coverage -maxdepth 2 -type f -print'
  ```
- **产出**：ERP测试框架/coverage provider确认；库存、订单或财务中的首个P0模块测试集。
- **验收**：703个既有测试全部通过；形成可复现覆盖率；新增 `>=20` 个测试；ERP基线之上提升 `>=4` 个百分点。
- **依赖**：MacMini可访问；先按 `package.json` 确认 Jest/Vitest 参数，命令不兼容时记录等价项目脚本。
- **时间**：8小时。
- **执行者**：cursor远程实现；coder执行报告。

## 第2周：覆盖率主攻并跨过60%

### Day 6：ERP第二批业务分支测试
- **具体命令**：
  ```bash
  ssh mac@10.31.1.177 'cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH npm test -- --coverage --runInBand'
  ssh mac@10.31.1.177 'cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH git diff --check'
  ```
- **产出**：ERP权限、校验失败、事务失败、重复请求和边界金额测试。
- **验收**：新增 `>=25` 个有效测试；ERP较Day 5再提升 `>=4` 个百分点；无快照滥用和无断言测试。
- **依赖**：Day 5覆盖率报告和测试夹具。
- **时间**：8小时。
- **执行者**：cursor实现；大锤80抽查10个用例。

### Day 7：股票系统测试框架和核心分析链路
- **具体命令**：
  ```bash
  cd /Users/maccc/daily_stock_analysis
  python3 -m pytest -q --collect-only
  python3 -m pytest -q --cov=. --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
  rg -n "requests|httpx|yfinance|akshare|pandas|read_csv|to_csv|datetime" . --glob '*.py'
  ```
- **产出**：行情源适配、数据清洗、指标计算、信号输出的隔离测试；外部数据源使用 fixture/mock。
- **验收**：测试数从3增至 `>=35`；核心计算使用固定输入验证精确结果；覆盖率 `>=45%`。
- **依赖**：Day 2股票清单；确认 `pytest.ini` 的收集和 marker 配置。
- **时间**：8小时。
- **执行者**：cursor编写；coder运行全量测试。

### Day 8：股票异常数据和日期边界测试
- **具体命令**：
  ```bash
  cd /Users/maccc/daily_stock_analysis
  python3 -m pytest -q --cov=. --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
  python3 -m pytest -q --count=3
  ```
- **产出**：停牌、缺失K线、复权、空结果、重复日期、时区、网络失败和缓存损坏测试。
- **验收**：测试总数 `>=60`；覆盖率 `>=60%`；连续3次结果一致。若无 `pytest-repeat`，用 shell 循环执行3次并记录。
- **依赖**：Day 7 fixture；禁止实时网络进入测试。
- **时间**：8小时。
- **执行者**：cursor实现；大锤80核验金融计算预期值。

### Day 9：台账核心导入、校验和汇总测试
- **具体命令**：
  ```bash
  cd /Users/maccc/Projects/ledger-quality-system
  .venv311/bin/python3 -m pytest -q --collect-only
  .venv311/bin/python3 -m pytest -q --cov=. --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
  rg -n "openpyxl|pandas|read_excel|read_csv|validate|reconcile|ledger" . --glob '*.py'
  ```
- **产出**：Excel/CSV导入、字段校验、重复记录、金额汇总和对账规则测试。
- **验收**：测试数从3增至 `>=40`；金额/日期精度有明确断言；覆盖率 `>=50%`。
- **依赖**：Day 2台账清单；脱敏构造小型 fixture。
- **时间**：8小时。
- **执行者**：cursor实现；coder采集覆盖率。

### Day 10：台账异常链路与覆盖率总闸
- **具体命令**：
  ```bash
  cd /Users/maccc/Projects/ledger-quality-system
  .venv311/bin/python3 -m pytest -q --cov=. --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
  cd /opt/dh-enterprise-factory && python3 -m pytest -q --cov=. --cov-report=json:coverage.json
  cd /Users/maccc/daily_stock_analysis && python3 -m pytest -q --cov=. --cov-report=json:coverage.json
  ```
- **产出**：台账异常文件、公式单元格、空工作表、并发写入、导出失败测试；四个重点系统中期覆盖率报告。
- **验收**：台账测试 `>=65`、覆盖率 `>=60%`；DH `>=58%`；股票保持 `>=60%`；加权总覆盖率首次达到或接近 `>=60%`。
- **依赖**：Days 3-9全部测试合入当前冲刺分支。
- **时间**：8小时。
- **执行者**：cursor补测；coder汇总；大锤80执行中期闸门评审。

## 第3周：Spec确认与AI修复样本工程

### Day 11：覆盖率缺口收口
- **具体命令**：
  ```bash
  cd /opt/dh-enterprise-factory && python3 -m pytest -q --cov=. --cov-fail-under=60 --cov-report=json:coverage.json
  ssh mac@10.31.1.177 'cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH npm test -- --coverage --runInBand'
  cd /Users/maccc/daily_stock_analysis && python3 -m pytest -q --cov=. --cov-fail-under=60
  cd /Users/maccc/Projects/ledger-quality-system && .venv311/bin/python3 -m pytest -q --cov=. --cov-fail-under=60
  ```
- **产出**：针对剩余高未覆盖分支的补充测试；覆盖率最终候选报告。
- **验收**：DH、股票、台账均 `>=60%`；ERP达到Day 1基线后确定的目标，且六系统加权 `>=60%`；商务保持 `>=68%`、SpecGuard保持 `>=87%`。
- **依赖**：Day 10中期报告；ERP单体低于50%时本日优先转为ERP补测。
- **时间**：8小时。
- **执行者**：cursor补测；coder重跑；大锤80确认无覆盖率排除项扩张。

### Day 12：股票Spec从骨架补全为可验证版本
- **具体命令**：
  ```bash
  cd /Users/maccc/daily_stock_analysis
  rg --files | rg -i 'spec|requirement|design|acceptance|test'
  rg -n "draft|TODO|TBD|待确认|验收|shall|必须" .
  python3 -m pytest -q --collect-only > /tmp/stock-test-inventory.txt
  ```
- **产出**：股票Spec补齐范围、术语、输入输出、数据时效、异常策略、非功能要求和逐条验收条件；状态改为 `review`。
- **验收**：每条需求具备唯一ID；无TBD；每条验收条件可由测试或人工检查判定。
- **依赖**：Days 7-8形成的真实行为和测试。
- **时间**：7小时。
- **执行者**：大锤80主写业务口径；cursor补技术细节。

### Day 13：股票Spec测试映射与confirmed签署
- **具体命令**：
  ```bash
  cd /Users/maccc/daily_stock_analysis
  python3 -m pytest -q --collect-only
  rg -n "REQ-[0-9]+|AC-[0-9]+" .
  python3 -m pytest -q
  ```
- **产出**：`REQ → AC → test nodeid`追踪矩阵、人工核验记录、confirmed版本及变更日志。
- **验收**：需求映射率、验收条件映射率均 `100%`；至少另一名执行者逐条复核；全量测试通过。
- **依赖**：Day 12 review版；测试名称或 marker 可稳定引用。
- **时间**：7小时。
- **执行者**：大锤80确认Spec；coder独立核验映射。

### Day 14：台账Spec补全、映射和确认
- **具体命令**：
  ```bash
  cd /Users/maccc/Projects/ledger-quality-system
  rg --files | rg -i 'spec|requirement|design|acceptance|test'
  rg -n "draft|TODO|TBD|待确认|验收|REQ-|AC-" .
  .venv311/bin/python3 -m pytest -q --collect-only > /tmp/ledger-test-inventory.txt
  .venv311/bin/python3 -m pytest -q
  ```
- **产出**：台账confirmed Spec、数据字典、金额/日期/重复项规则、`REQ → AC → test nodeid`矩阵和核验记录。
- **验收**：无TBD；映射率 `100%`；关键财务规则由人工样例与自动化测试双重核验。
- **依赖**：Days 9-10测试；业务规则负责人可在当日完成确认。
- **时间**：8小时。
- **执行者**：大锤80确认规则；cursor维护映射；coder复跑测试。

### Day 15：AI修复100样本集定义与冻结首批样本
- **具体命令**：
  ```bash
  curl -fsS http://127.0.0.1:9100/openapi.json | python3 -m json.tool > /tmp/ai-fix-openapi.pretty.json
  launchctl list | rg -i 'fix|repair|9100'
  log show --last 14d --style json --predicate 'eventMessage CONTAINS[c] "9100" OR process CONTAINS[c] "repair"' > /tmp/ai-fix-14d.json
  rg -n "success|failed|patch|repair|sample" /tmp/ai-fix-14d.json
  ```
- **产出**：100样本规范：语言/系统/错误类型/难度分层、成功判定、去重规则、隐私规则；冻结首批 `>=50` 个历史样本。
- **验收**：每个样本包含原始提交、失败日志、期望测试、允许修改范围和唯一ID；6/31旧样本保留且不重复计数。
- **依赖**：Day 1 API与服务清单；若统一日志不含请求体，从编排器持久化目录只读导出。
- **时间**：8小时。
- **执行者**：coder采集清洗；大锤80定义成功判据。

## 第4周：AI修复达标、逆向数据集验证和总验收

### Day 16：AI修复失败分类与第一轮改进
- **具体命令**：
  ```bash
  curl -fsS http://127.0.0.1:9100/health
  rg -n "prompt|patch|apply|pytest|test|timeout|retry|context" /Users/maccc/projects /opt/dh-enterprise-factory --glob '*.py' --glob '*.json' --glob '*.yaml'
  curl -fsS http://127.0.0.1:9100/openapi.json | jq -r '.paths | keys[]'
  ```
- **产出**：25个失败样本根因分类；修复补丁聚焦上下文截断、补丁应用、测试命令选择、超时或结果判定。
- **验收**：每项代码改动关联至少一个失败样本和回归测试；开发集成功率由19%提升到 `>=35%`。
- **依赖**：Day 15样本规范；先从OpenAPI确认真实提交/结果端点，不猜测接口。
- **时间**：8小时。
- **执行者**：cursor实现修复；coder跑开发集；大锤80审查失败分类。

### Day 17：补足100样本并完成第二轮AI修复
- **具体命令**：
  ```bash
  log show --last 30d --style json --predicate 'eventMessage CONTAINS[c] "repair" OR eventMessage CONTAINS[c] "patch"' > /tmp/ai-fix-30d.json
  curl -fsS http://127.0.0.1:9100/openapi.json | jq '.paths'
  launchctl print gui/$(id -u) | rg -n -i 'repair|fix|9100'
  ```
- **产出**：100个去重、分层、脱敏样本；开发/验证/冻结测试集按60/20/20划分；第二轮修复和回归测试。
- **验收**：100样本字段完整率 `100%`；无同源重复泄漏；开发+验证集成功率 `>=50%`，冻结20样本仍未用于调参。
- **依赖**：Day 16修复版本；每2小时任务持续运行并保留原始证据。
- **时间**：8小时。
- **执行者**：coder整理样本；cursor修复；大锤80抽查20个样本。

### Day 18：逆向引擎数据集构建与双人标注
- **具体命令**：
  ```bash
  cd /Users/maccc/projects/specguard
  rg -n "regex|re\.compile|reverse|extract|pattern|rule" . --glob '*.py'
  rg --files | rg -i 'fixture|dataset|corpus|gold|reverse|test'
  .venv/bin/python -m pytest -q
  ```
- **产出**：覆盖83%正则规则的标注数据集，至少120条，包含正例、硬负例、多行、格式变体和冲突规则；生成规则覆盖矩阵。
- **验收**：每条规则至少2个正例和1个硬负例；20%样本双人独立标注，一致率 `>=90%`；数据脱敏。
- **依赖**：定位逆向引擎真实模块；大锤80提供语义金标，coder完成结构化。
- **时间**：8小时。
- **执行者**：大锤80与coder双人标注；cursor编写数据加载器。

### Day 19：冻结评测与缺陷修复
- **具体命令**：
  ```bash
  cd /Users/maccc/projects/specguard
  .venv/bin/python -m pytest -q
  .venv/bin/python -m pytest -q --cov=. --cov-report=term-missing
  rg -n "false_positive|false_negative|precision|recall|f1|dataset" tests . --glob '*.py'
  ```
- **产出**：逆向引擎80/20分层数据集、评测脚本、precision/recall/F1和逐规则错误报告；AI修复100样本最终盲测报告。
- **验收**：逆向测试集在运行前冻结并记录SHA-256；全部规则有数据验证结果；AI修复100样本一次盲测成功 `>=50/100`，失败样本均有原因标签。
- **依赖**：Days 17-18；AI评测使用固定模型、参数、超时和环境。
- **时间**：8小时。
- **执行者**：coder执行盲测；大锤80监证；cursor只修复逆向引擎开发集暴露的问题。

### Day 20：全系统总验收与SDD证据包
- **具体命令**：
  ```bash
  cd /Users/maccc/projects/business-document-generator && .venv/bin/python -m pytest -q --cov=. --cov-report=json:coverage.json
  cd /Users/maccc/projects/specguard && .venv/bin/python -m pytest -q --cov=. --cov-report=json:coverage.json
  cd /opt/dh-enterprise-factory && python3 -m pytest -q --cov=. --cov-fail-under=60 --cov-report=json:coverage.json
  ssh mac@10.31.1.177 'cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH npm test -- --coverage --runInBand'
  cd /Users/maccc/daily_stock_analysis && python3 -m pytest -q --cov=. --cov-fail-under=60 --cov-report=json:coverage.json
  cd /Users/maccc/Projects/ledger-quality-system && .venv311/bin/python3 -m pytest -q --cov=. --cov-fail-under=60 --cov-report=json:coverage.json
  shasum -a 256 /tmp/cloud3-containers.txt /tmp/ai-fix-openapi.json /tmp/review-agent-openapi.json
  ```
- **产出**：`SDD-20day-final.md`、覆盖率汇总、测试日志、两份confirmed Spec及映射、AI修复100样本报告、逆向数据集报告、证据文件SHA-256清单。
- **验收**：六系统加权覆盖率 `>=60%`；股票和台账Spec confirmed且映射 `100%`；AI修复 `>=50/100`；逆向引擎完成冻结数据集验证；SDD复评 `>=20/24`，目标值 **20.6/24**。
- **依赖**：Days 1-19全部证据；cloud3保持只读，任何无法采集的指标必须有权限限制说明和容器外证据。
- **时间**：8小时。
- **执行者**：coder执行全量回归和归档；大锤80最终签署；cursor处理仅限测试/环境类阻断。

## 每日固定机制

- 每天09:30记录前一日测试数、覆盖率、Spec映射率、AI累计样本数和逆向数据集条数。
- 每天17:30运行受影响系统全量测试；失败不得带入下一工作日，环境故障需附日志和责任人。
- AI修复每2小时、审查Agent每6小时、覆盖率cron每日11:00、编排器每5分钟的现有调度保持运行；冲刺期间不以手工成功替代自动任务结果。
- 每日证据统一包含：日期、仓库、commit SHA、命令、退出码、测试数、指标、日志路径、执行者和复核者。
- **止损线**：Day 10加权覆盖率仍低于55%时，暂停非必要Spec写作1天投入ERP/DH补测；Day 17 AI验证集低于40%时，不得直接评测冻结集，先修复样本质量或执行链路。
