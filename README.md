# SpecGuard — 企业级SDD治理平台

> **SDD领域的SonarQube** — 不是Lint工具，是持续治理平台

## 快速开始

```bash
# 安装
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 启动
uvicorn app.main:app --reload --port 8700

# API文档
open http://localhost:8700/docs
```

## 核心功能

- 🔒 **Spec门禁引擎** — PR必须有Spec引用，自动校验frontmatter
- 📊 **覆盖率看板** — 按Spec ID追踪覆盖率，自动提升任务
- 🔍 **CI状态检测** — GitHub Actions绿灯监控
- 🏗️ **代码逆向引擎** — 存量代码→Spec自动生成（V0.3）

## 文档

- [平台方案V2](sdd/SPECGUARD-PLATFORM-V2.md)
- [API文档](http://localhost:8700/docs)

## License

Apache 2.0
