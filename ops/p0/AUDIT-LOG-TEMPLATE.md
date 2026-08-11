# SDD审计日志模板

## 每次变更必须记录
- timestamp: ISO8601
- actor: 大锤80/cursor/coder/AI修复/cron
- system: 目标系统
- action: create/update/delete/deploy/repair
- before_state: 变更前状态
- after_state: 变更后状态
- evidence: git commit SHA / test result / coverage report
- approved_by: 审批人(自动=cron, 人工=名字)

## 不可篡改
- 日志追加写入(append-only)
- HMAC签名(可选)
- 定期备份到/backup/
