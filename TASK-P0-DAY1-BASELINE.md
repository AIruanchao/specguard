# 任务卡: P0 Day1 — 七系统基线冻结

## 背景
SDD从12.6/24升级到18+/24，P0第一阶段。Day1冻结7个系统的测试+覆盖率+CI基线。

## 执行步骤

### 1. 创建基线目录
```bash
mkdir -p /Users/maccc/projects/specguard/ops/p0/baselines
```

### 2. 跑7个系统的基线

每个系统跑pytest+coverage，结果写入baselines/：

- 商务FastAPI: `cd /Users/maccc/projects/business-document-generator && .venv/bin/python -m pytest --cov=. --cov-report=term-missing -q --tb=no > /Users/maccc/projects/specguard/ops/p0/baselines/business-tests.txt 2>&1`
- SpecGuard: `cd /Users/maccc/projects/specguard && .venv/bin/python -m pytest --cov=. --cov-report=term-missing -q --tb=no > ops/p0/baselines/specguard-tests.txt 2>&1`
- DH工厂: `cd /opt/dh-enterprise-factory && python3 -m pytest --cov=. --cov-report=term-missing -q --tb=no > /Users/maccc/projects/specguard/ops/p0/baselines/dh-tests.txt 2>&1`
- 股票: `cd /Users/maccc/daily_stock_analysis && python3 -m pytest --collect-only -q > /Users/maccc/projects/specguard/ops/p0/baselines/stock-collect.txt 2>&1`
- 台账: `cd /Users/maccc/Projects/ledger-quality-system && .venv311/bin/python3 -m pytest --collect-only -q > /Users/maccc/projects/specguard/ops/p0/baselines/ledger-collect.txt 2>&1`
- ERP: `ssh mac@10.31.1.177 "cd /Users/mac/erp-project && npm test -- --run 2>&1 | tail -10" > /Users/maccc/projects/specguard/ops/p0/baselines/erp-tests.txt 2>&1`
- cloud3: `ssh root@124.222.234.8 "docker ps --format '{{.Names}}\t{{.Status}}'" > /Users/maccc/projects/specguard/ops/p0/baselines/cloud3-containers.txt 2>&1`

### 3. 写基线报告
生成 `/Users/maccc/projects/specguard/ops/p0/P0-BASELINE.md`，含7系统测试状态+覆盖率+CI状态。

## 验收
- [ ] baselines/目录至少7个非空文件
- [ ] P0-BASELINE.md包含7系统数据

## 约束
- 只在SpecGuard项目的ops/p0/目录操作
- 不修改任何目标系统的代码
