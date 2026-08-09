作为顶级工程架构师，针对当前多路径、多状态（特别是包含远程MacMini节点）、覆盖率与CI缺失的异构系统现状，我为你设计了**P0级别（10个工作日）的“天级”落地执行计划**。

> **架构师批注**：原需求中提到“4个缺CI的系统”，但根据现状表，**实际只有3个系统（ERP、股票、台账）缺失CI**。本计划按3个系统进行CI部署，并对原有3个系统的CI进行统一化改造。

---

### Week 1: 基础摸底与破冰 (统一资产与基线测量)

#### P0-Day1-任务1: 建立全局资产清单规范与模板 (架构师)
- **命令**: 
  ```bash
  mkdir -p ~/.sdd/templates && cat > ~/.sdd/templates/sdd-manifest.yaml << 'EOF'
  project_name: "SAMPLE"
  language: "Python/NodeJS/etc"
  ci_status: "enabled/disabled"
  coverage:
    type: "pytest/jest/go-test"
    current: 0%
  zero_debt_rules:
    max_complexity: 10
    blocking_on_todo: true
  EOF
  ```
- **产出**: `~/.sdd/templates/sdd-manifest.yaml` (标准模板文件)
- **验收**: `cat ~/.sdd/templates/sdd-manifest.yaml` -> 预期：成功输出上述YAML内容
- **依赖**: 无
- **时间**: 1h

#### P0-Day1-任务2: 6系统清单文件初始化 (后端团队)
- **命令**: 
  ```bash
  # 在6个项目的根目录分别执行拷贝
  cp ~/.sdd/templates/sdd-manifest.yaml /Users/maccc/projects/business-document-generator/sdd-manifest.yaml
  # ...(其他5个项目同理，ERP需scp到MacMini)
  ```
- **产出**: 6个系统根目录下生成 `sdd-manifest.yaml`
- **验收**: `find /Users/maccc/projects /opt/dh-enterprise-factory -name "sdd-manifest.yaml" | wc -l` -> 预期输出: `3` (其余各自验证)
- **依赖**: 任务1完成
- **时间**: 2h

#### P0-Day2-任务1: 股票与台账系统测试环境破冰 (全栈工程师)
- **命令**: 
  ```bash
  cd /Users/maccc/daily_stock_analysis && pip install pytest pytest-cov && pytest --co
  cd /Users/maccc/Projects/ledger-quality-system && pip install pytest pytest-cov && pytest --co
  ```
- **产出**: 两个项目生成 `.coveragerc` 配置文件及依赖文件更新 (`requirements-dev.txt`)
- **验收**: `pytest --co -q` -> 预期：无报错，输出发现的测试用例数量（即使是0也算成功，证明环境可跑）
- **依赖**: Day1-任务2完成
- **时间**: 4h

#### P0-Day2-任务2: 远程ERP系统测试环境破冰 (运维工程师)
- **命令**: 
  ```bash
  ssh mac@MacMini "cd /Users/mac/erp-project && pip install pytest pytest-cov && pytest --co"
  ```
- **产出**: ERP系统内生成 `.coveragerc`
- **验收**: SSH终端返回无报错，成功扫描测试树结构
- **依赖**: MacMini网络打通
- **时间**: 4h

#### P0-Day3-任务1: 未测系统(股票/台账/ERP)跑第一次覆盖率 (测试工程师)
- **命令**: 
  ```bash
  # 股票与台账本地执行
  cd /Users/maccc/daily_stock_analysis && pytest --cov=. --cov-report=xml:coverage.xml
  cd /Users/maccc/Projects/ledger-quality-system && pytest --cov=. --cov-report=xml:coverage.xml
  # ERP远程执行
  ssh mac@MacMini "cd /Users/mac/erp-project && pytest --cov=. --cov-report=xml:coverage.xml"
  ```
- **产出**: 3个系统各自生成 `coverage.xml` 与终端覆盖率报告
- **验收**: 查看终端输出，成功打印出 `TOTAL` 覆盖率百分比（无论多少）
- **依赖**: Day2任务完成
- **时间**: 3h

#### P0-Day3-任务2: 已测系统基线测量与打平 (测试工程师)
- **命令**: 
  ```bash
  cd /Users/maccc/projects/business-document-generator && pytest --cov=. --cov-report=xml:coverage.xml
  cd /Users/maccc/projects/specguard && pytest --cov=. --cov-report=xml:coverage.xml
  cd /opt/dh-enterprise-factory && go test ./... -coverprofile=coverage.out
  ```
- **产出**: 3个已测系统的标准格式的 `coverage.xml` / `coverage.out`
- **验收**: `ls -l coverage.*` -> 预期：成功生成覆盖率原始文件
- **依赖**: 无
- **时间**: 3h

#### P0-Day4-任务1: 6系统覆盖率基线汇总入库 (架构师)
- **命令**: 
  ```bash
  # 编写解析脚本提取XML中的line-rate，写入各自manifest
  # 示例伪命令：
  parse_and_update_coverage() { xmlstarlet sel -t -m "//coverage" -v "@line-rate" $1/coverage.xml; }
  ```
- **产出**: 6个系统的 `sdd-manifest.yaml` 中 `coverage.current` 字段更新为真实测量值
- **验收**: `grep "current:" */sdd-manifest.yaml` -> 预期：输出45%, 81%, 32%, 及新测出的3个数值
- **依赖**: Day3任务完成
- **时间**: 3h

#### P0-Day4-任务2: 建立统一CI模板规范 (DevOps工程师)
- **命令**: 
  ```bash
  cat > ~/.sdd/templates/sdd-ci-template.yml << 'EOF'
  stages:
    - test
    - coverage
  include:
    - template: Coverage-Merge.gitlab-ci.yml # 或GitHub Actions复用Workflow
  EOF
  ```
- **产出**: 统一的CI标准YAML片段
- **验收**: YAML语法Lint检查通过 (`yamllint`)
- **依赖**: 无
- **时间**: 4h

#### P0-Day5-任务1: 股票与台账CI流水线部署 (DevOps工程师)
- **命令**: 
  ```bash
  # 股票
  cd /Users/maccc/daily_stock_analysis
  mkdir -p .github/workflows && cp ~/.sdd/templates/sdd-ci-template.yml .github/workflows/sdd-pipeline.yml
  git add . && git commit -m "ci: setup unified SDD pipeline and coverage report" && git push
  # 台账同上
  ```
- **产出**: 两个仓库新增CI流水线配置文件，且GitHub/GitLab后台触发第一次CI构建
- **验收**: 查看CI面板，Build状态由黄变绿，Artifacts中包含 `coverage.xml`
- **依赖**: Day4-任务2完成
- **时间**: 4h

---

### Week 2: 统一规则与闭环 (统一CI与零欠项实施)

#### P0-Day6-任务1: 远程ERP系统CI流水线部署 (DevOps工程师)
- **命令**: 
  ```bash
  ssh mac@MacMini << 'EOF'
  cd /Users/mac/erp-project
  mkdir -p .github/workflows 
  cp ~/.sdd/templates/sdd-ci-template.yml .github/workflows/sdd-pipeline.yml
  # 注意ERP需配置GitHub Actions self-hosted runner (MacMini节点)
  git add . && git commit -m "ci: bootstrap ERP pipeline" && git push
  EOF
  ```
- **产出**: ERP仓库新增CI文件，触发构建。MacMini被注册为Self-hosted Runner。
- **验收**: 远程执行 `git log -1` 显示提交，CI平台显示ERP任务被分发到MacMini执行并成功。
- **依赖**: Day4-任务2完成，MacMini Runner注册完毕
- **时间**: 4h

#### P0-Day6-任务2: 3个老系统CI统一化改造 (DevOps工程师)
- **命令**: 
  ```bash
  # 针对商务单据、SpecGuard、DH工厂
  # 将原各异的CI脚本替换为引用 sdd-ci-template.yml
  git -C /Users/maccc/projects/business-document-generator commit -am "refactor(ci): align with SDD standard"
  ```
- **产出**: 3个老系统CI配置文件更新并Push
- **验收**: 3个老系统的CI重新触发，流水线Stages名称完全一致，成功通过。
- **依赖**: Day4-任务2完成
- **时间**: 4h

#### P0-Day7-任务1: 统一零欠项规则引擎配置 (架构师)
- **命令**: 
  ```bash
  # 以Python为例，配置 .flake8 和 pytest strict模式
  cat > ~/.sdd/templates/.flake8 << 'EOF'
  [flake8]
  max-complexity = 10
  select = C901,F401,F811,TODO
  EOF
  ```
- **产出**: 统一的静态检查规则模板 (包含复杂度限制、TODO/FIXME阻断机制)
- **验收**: 模板文件创建完成，规则审查通过。
- **依赖**: 无
- **时间**: 2h

#### P0-Day7-任务2: 6系统零欠项规则本地落地 (后端团队)
- **命令**: 
  ```bash
  # 在6个系统分别执行拷贝和应用
  cp ~/.sdd/templates/.flake8 /Users/maccc/Projects/ledger-quality-system/.flake8
  # ERP使用scp传输
  ```
- **产出**: 6个系统根目录生成零欠项规则配置文件
- **验收**: 在项目中执行 `flake8 .`，能正确扫描出TODO或复杂度问题（允许此时有报错，仅验证规则生效）
- **依赖**: 任务1完成
- **时间**: 3h

#### P0-Day8-任务1: 全系统技术债清理 (技术债务爆破小队)
- **命令**: 
  ```bash
  # 逐系统执行，修复或忽略(必须写明带issue编号的NOQA)
  flake8 /Users/maccc/daily_stock_analysis/
  # 运行修复，如：重构高复杂度函数，消除无用的import等
  ```
- **产出**: 6系统的 `flake8 .` 和复杂度扫描返回状态码 0 (Success)
- **验收**: `echo $?` -> 输出 `0`
- **依赖**: Day7任务完成
- **时间**: 6h (全天集中清欠)

#### P0-Day9-任务1: CI卡点熔断机制接入 (DevOps工程师)
- **命令**: 
  ```bash
  # 在 sdd-ci-template.yml 中添加断言：
  # - pytest --cov --cov-fail-under=$(grep current sdd-manifest.yaml | awk '{print $2*100}')
  # - flake8 .
  ```
- **产出**: 统一更新后的 `sdd-ci-template.yml`，并分发给6个系统提交。
- **验收**: 故意在股票系统写一行 `import os` 不用，`git push`后CI直接**Red (Fail)**。删除后CI变**Green (Pass)**。
- **依赖**: Day8任务完成 (否则CI会一直红)
- **时间**: 4h

#### P0-Day10-任务1: P0阶段验收与基线冻结报告 (架构师)
- **命令**: 
  ```bash
  # 聚合请求：检查所有仓库最后一次CI状态
  gh run list --repo ... # (或GitLab API调用)
  # 提取最新的coverage并更新到总清单表
  ```
- **产出**: `P0_Upgrade_Acceptance_Report.md` (含最终的覆盖率基线表和CI状态红绿灯)
- **验收**: 报告呈现：6个系统CI=✅，覆盖率基线已确立，且当前分支全部为零TODO/FIXME干净状态。
- **依赖**: Day9任务完成
- **时间**: 4h