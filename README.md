<div align="center">

# 🛡️ SpecGuard

### SDD领域的SonarQube — 企业级Spec-Driven Development治理平台

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-23%20passed-brightgreen.svg)](#)

**棕地友好 · 多项目治理 · CI门禁 · 覆盖率看板 · 代码逆向引擎**

</div>

---

## 📖 什么是SpecGuard

SpecGuard是一个**独立的Web服务平台**，帮助团队在存量（棕地）项目中落地Spec-Driven Development（规格驱动开发）。

**核心价值**: 把"写完没人看"的文档变成能真正卡住AI输出的执行性合约。

### 与其他SDD工具的区别

| 维度 | SpecGuard | GitHub Spec-Kit | AWS Kiro | OpenSpec |
|------|-----------|-----------------|----------|----------|
| **形态** | Web服务+API | CLI工具 | IDE | CLI命令 |
| **棕地支持** | ✅ A/B/C分级+逆向解析 | ❌ | ❌ | ⚠️ delta |
| **CI门禁** | ✅ Python+frontmatter | ❌ 手动 | ❌ | ❌ |
| **覆盖率看板** | ✅ SDD场景独占 | ❌ | ❌ | ❌ |
| **代码逆向** | ✅ AST→Spec自动生成 | ❌ | ❌ | ❌ |
| **自部署** | ✅ Docker | ✅ | ❌ AWS | ✅ |

## 🚀 快速开始

### Docker部署（推荐）

```bash
git clone https://github.com/AIruanchao/specguard.git
cd specguard
cp .env.example .env
docker-compose up -d
```

访问 http://localhost:8700

### 本地开发

```bash
git clone https://github.com/AIruanchao/specguard.git
cd specguard
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8700
```

## 📐 架构

```
┌─────────────────────────────────────────────┐
│              SpecGuard Platform              │
│                                             │
│  Web UI (4页面)        REST API (Swagger)   │
│  ┌─────────────────┐  ┌──────────────────┐ │
│  │ Dashboard总览   │  │ /api/v1/health   │ │
│  │ 覆盖率热力图    │  │ /api/v1/gate     │ │
│  │ Spec列表        │  │ /api/v1/coverage │ │
│  │ 门禁检查器      │  │ /api/v1/ci       │ │
│  │                 │  │ /api/v1/specs    │ │
│  │                 │  │ /api/v1/reverse  │ │
│  └─────────────────┘  └──────────────────┘ │
│                                             │
│  Core Engines                               │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ 门禁引擎  │ │ 覆盖率   │ │ 逆向引擎   │  │
│  │ (Spec    │ │ (pytest  │ │ (Python    │  │
│  │  front-  │ │  --cov   │ │  AST分析)  │  │
│  │  matter) │ │  集成)   │ │            │  │
│  └──────────┘ └──────────┘ └────────────┘  │
└─────────────────────────────────────────────┘
```

## 🔧 核心功能

### 1. Spec门禁引擎
- PR必须有Spec文件引用（`sdd/domain-spec/xxx/spec.md`）
- YAML frontmatter自动校验（spec_id/module/level/status）
- A级strict / B级warn / C级豁免
- hotfix 72小时追踪闭环

### 2. 覆盖率看板
- 按A级模块追踪覆盖率（7维度风险矩阵）
- 覆盖率爬坡目标（44%→65%→75%→80%）
- 自动生成覆盖率缺口任务卡
- Golden Case + 变异测试验证

### 3. 代码逆向引擎
- AST分析 → 函数签名/类型注解/import图
- 路由提取 → FastAPI装饰器→OpenAPI Schema
- 模型提取 → Pydantic Model→数据字典
- 三段式分类 → 已确认事实/推断规则/待澄清项

### 4. CI状态检测
- GitHub Actions运行状态监控
- 自动检测CI红灯并通知

## 📋 API文档

启动后访问 http://localhost:8700/docs 查看完整Swagger UI。

### 主要端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/gate/check` | PR门禁检查 |
| GET | `/api/v1/coverage/{project}` | 项目覆盖率 |
| POST | `/api/v1/coverage/analyze` | 覆盖率缺口分析 |
| GET | `/api/v1/ci/status` | CI状态查询 |
| GET | `/api/v1/specs/list` | Spec文件列表 |
| POST | `/api/v1/reverse/analyze` | 代码逆向分析 |

## 🗺️ 路线图

| 版本 | 功能 | 状态 |
|------|------|------|
| V0.1 | REST API（门禁/覆盖率/CI） | ✅ |
| V0.2 | Web UI（Dashboard/覆盖率/Spec/门禁） | ✅ |
| V0.3 | 逆向引擎MVP（AST+路由+模型提取） | ✅ |
| **V1.0** | **Docker部署+文档+开源** | ✅ |
| V1.5 | 多项目+PostgreSQL+认证 | 📋 |
| V2.0 | GitHub App+逆向引擎完整版 | 📋 |
| V2.5 | 多模型投票（可选） | 📋 |

## 🤝 贡献

欢迎提交Issue和PR！

## 📄 License

[Apache 2.0](LICENSE)

## 🙏 致谢

- [GitHub Spec-Kit](https://github.com/github/spec-kit) — SDD理念启发
- [OpenSpec](https://github.com/Fission-AI/OpenSpec) — delta变更管理
- [Thoughtworks](https://www.thoughtworks.com/en-in/radar/techniques/spec-driven-development) — 棕地改造方法论
