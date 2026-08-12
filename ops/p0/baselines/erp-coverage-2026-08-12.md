# ERP覆盖率基线 (2026-08-12)

## 执行命令
```
ssh mac@10.31.1.177 "cd /Users/mac/erp-project && PATH=/usr/local/bin:$PATH npx vitest run src/lib --coverage --config vitest.config.cov.mjs"
```

## 测试结果
- Test Files: 98 passed (98)
- Tests: 607 passed (607)
- 失败: 0 (仅 src/lib 范围)

## 覆盖率数据 (src/lib/**/*.ts, exclude tsx/test)
| 维度 | 覆盖率 |
|------|--------|
| Statements | 11.37% (2280/20039) |
| Branches   | 9.12%  (1513/16588) |
| Functions  | 13.74% (379/2757) |
| Lines      | 12.09% (2093/17300) |

## 全量测试结果（npm test）
- Test Files: 109 passed / 3 failed
- Tests: 703 passed / 1 failed
- 失败项: src/__tests__/feishu-client.test.ts > upsertRecord创建时过滤受保护字段
- E2E失败: tests/e2e/core-business.spec.ts, tests/e2e/form-crud.spec.ts (Playwright配置错误)

## 已知限制
- vitest 4.1.9 + @vitest/coverage-v8 4.1.9 在UncoveredFiles阶段静默失败
- 解决: include限定到`src/lib/**/*.ts` + filter到 `src/lib` 才输出报告
- 完整全量coverage需要v8升级到4.1.10+或换@vitest/coverage-istanbul

## 备注
- 全量包含tsx/app/routes后覆盖率会显著上升
- 此基线仅作"src/lib模块"基线，全量基线需要修复v8 provider后再采
