# SDD系统SLA定义

| 系统 | 可用性 | RTO | RPO | 监控 |
|------|--------|-----|-----|------|
| SpecGuard | 99% | 5min | 0 | launchd KeepAlive |
| AI修复系统 | 99% | 5min | 0 | launchd每2h |
| 审查Agent | 99% | 5min | 0 | launchd每6h |
| 覆盖率cron | 95% | 1h | 0 | cron每日11:00 |
| Spec质量cron | 95% | 1h | 0 | cron每日12:00 |

## 告警规则
- 服务离线>10min → 飞书告警
- cron连续3次失败 → 飞书告警
- 覆盖率下降>5% → 飞书告警
