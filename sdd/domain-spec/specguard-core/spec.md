# SpecGuard Core Spec

## status: confirmed

## Confirmed Facts
- SpecGuard是FastAPI应用, 端口8700, launchd常驻
- API: /api/v1/health, /api/v1/gate/check, /api/v1/coverage/, /api/v1/ci/status
- V1.5: 32测试, 87%覆盖率, TS逆向引擎, Docker
- CI: GitHub Actions, coverage门禁≥80%
