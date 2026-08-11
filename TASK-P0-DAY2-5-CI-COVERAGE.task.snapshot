# 任务卡: P0 Day2-5 — 统一CI门禁契约 + 3系统覆盖率基线

## 项目位置
`/Users/maccc/projects/specguard`

## 需要开发的文件

### 1. 统一CI门禁契约（Day2）
创建以下文件：
- `specs/quality/ci-gate-policy.md` — 7阶段CI门禁定义
- `schemas/ci-evidence.schema.json` — CI证据JSON Schema
- `ops/p0/templates/sdd-python-ci.yml` — Python系统CI模板
- `ops/p0/templates/sdd-nextjs-ci.yml` — Next.js系统CI模板

### sdd-python-ci.yml 内容
```yaml
name: SDD CI
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: python -m pytest --cov=. --cov-report=term-missing --cov-report=xml --tb=short
      - run: python -m py_compile app/main.py
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml
```

### sdd-nextjs-ci.yml 内容
```yaml
name: SDD CI
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run lint --if-present
      - run: npm test -- --run --coverage
      - run: npm run build --if-present
```

### 2. 股票系统最小测试（Day4）
在 `/Users/maccc/daily_stock_analysis/tests/` 创建：
- `tests/__init__.py`
- `tests/test_main.py` — 至少3个测试(test_health/test_import/test_config)

### 3. 台账系统最小测试（Day5）
在 `/Users/maccc/Projects/ledger-quality-system/tests/` 补：
- `tests/unit/test_config.py` — 至少3个测试

### 4. 3个缺CI系统的GitHub Actions
- 股票: `/Users/maccc/daily_stock_analysis/.github/workflows/ci.yml`
- 台账: `/Users/maccc/Projects/ledger-quality-system/.github/workflows/ci.yml`
- ERP: 在MacMini上创建(SpecGuard远程SSH)

## 验收标准
- [ ] ci-gate-policy.md存在且包含7阶段定义
- [ ] sdd-python-ci.yml和sdd-nextjs-ci.yml语法正确
- [ ] 股票系统至少3个pytest测试
- [ ] 台账系统至少3个pytest测试
- [ ] 3个系统的.github/workflows/ci.yml存在
- [ ] 股票系统: python3 -m pytest tests/ → 3+ passed
- [ ] 台账系统: .venv311/bin/python3 -m pytest tests/unit/test_config.py → 3+ passed

## 约束
- 不修改现有业务代码
- 只创建测试文件和CI配置
- 全英文代码注释
