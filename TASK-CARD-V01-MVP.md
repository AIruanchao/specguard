# Cursor任务卡: SpecGuard V0.1 MVP

## 目标

用FastAPI包装现有的3个SDD脚本，构建SpecGuard平台的最小可用API。

## 项目位置

`/Users/maccc/projects/specguard`

## 技术栈

- Python 3.11 + FastAPI + Pydantic
- 无数据库（V0.1纯API，V1.5加PostgreSQL）
- 无认证（V0.1开放API，V1.5加JWT）

## 需要开发的文件

```
specguard/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI入口
│   ├── config.py             # 配置管理（读.env）
│   ├── models.py             # Pydantic模型
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── gate.py           # 门禁引擎API
│   │   ├── coverage.py       # 覆盖率引擎API
│   │   ├── ci.py             # CI检查API
│   │   └── health.py         # 健康检查
│   └── services/
│       ├── __init__.py
│       ├── gate_service.py   # 包装spec_gate.py逻辑
│       ├── coverage_service.py # 包装coverage-auto-improve.py逻辑
│       └── ci_service.py     # 包装ci-green-check.py逻辑
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_gate.py
│   ├── test_coverage.py
│   ├── test_ci.py
│   └── test_health.py
├── requirements.txt          # 已创建
├── .env.example              # 已创建
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
└── README.md                 # 已创建
```

## API设计

### 1. 健康检查

```
GET /api/v1/health
→ {"status": "healthy", "service": "specguard", "version": "0.1.0"}
```

### 2. 门禁引擎

```
POST /api/v1/gate/check
Body:
{
  "project_path": "/Users/maccc/projects/business-document-generator",
  "changed_files": ["app/services/smart_seal.py"],
  "pr_body": "修复骑缝章 Spec: sdd/domain-spec/seal-engine/spec.md",
  "pr_labels": []
}
→
{
  "passed": true,
  "affected_modules": ["seal-engine"],
  "spec_refs": ["sdd/domain-spec/seal-engine/spec.md"],
  "errors": [],
  "warnings": []
}
```

### 3. 覆盖率引擎

```
GET /api/v1/coverage/{project_name}
→
{
  "project": "business-document-generator",
  "total_coverage": 45.0,
  "modules": [
    {"module": "seal-engine", "coverage": 14.8, "level": "A", "target": 80},
    {"module": "auth", "coverage": 100.0, "level": "A", "target": 80},
    ...
  ]
}

POST /api/v1/coverage/analyze
Body:
{
  "project_path": "/Users/maccc/projects/business-document-generator"
}
→
{
  "gaps": [...],
  "task_card_path": "sdd/change-log/TASK-COVERAGE-xxx.md"
}
```

### 4. CI检查

```
GET /api/v1/ci/status?repo=AIruanchao/business-document-generator
→
{
  "repo": "AIruanchao/business-document-generator",
  "latest_run": {
    "status": "completed",
    "conclusion": "success",
    "name": "CI",
    "url": "https://github.com/..."
  }
}
```

## 现有脚本的复用

门禁/覆盖率/CI的核心逻辑直接从business-document-generator项目的sdd/scripts/复制以下文件：

1. `spec_gate.py` → `app/services/gate_service.py`（核心逻辑）
2. `coverage-auto-improve.py` → `app/services/coverage_service.py`
3. `ci-green-check.py` → `app/services/ci_service.py`
4. `module_paths.json` → 放在`app/data/`目录

**关键**: 不要import外部项目，把核心逻辑复制到specguard/app/services/内，做成独立可运行的服务。

## Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8700
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8700"]
```

## docker-compose.yml

```yaml
version: '3.8'
services:
  specguard:
    build: .
    ports:
      - "8700:8700"
    env_file: .env
    volumes:
      - ./data:/app/data
```

## pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

## 验收标准

1. `python -m pytest tests/ -q` → 全绿
2. `uvicorn app.main:app` 启动无报错
3. `curl http://localhost:8700/api/v1/health` → 返回200
4. `curl http://localhost:8700/docs` → Swagger UI可访问
5. POST /api/v1/gate/check 用上面示例数据 → 返回passed=true
6. Docker build成功

## 约束

- 不要用SQLAlchemy/数据库（V0.1纯API）
- 不要加认证（V0.1开放）
- 不要加Web UI（V0.2做）
- 核心逻辑从现有脚本复制，不要重新设计
- 全英文代码注释，全中文错误消息
