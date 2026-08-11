# CI Gate Policy v1.0

## 7-Stage Pipeline
1. checkout/install
2. lint (ruff/eslint)
3. unit-test (pytest/vitest)
4. coverage (>=baseline)
5. spec-check (sdd/ reference)
6. build (py_compile/next build)
7. deployment-smoke (health check)

## Rules
- All tests must exit code 0
- No continue-on-error
- Coverage must not drop below frozen baseline
- CI evidence retained 30+ days
- Main branch merge requires all checks pass
