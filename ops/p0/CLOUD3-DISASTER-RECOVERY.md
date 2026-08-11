# cloud3 灾备策略

## Docker容器
| 容器 | 镜像 | 重启策略 | 备份方式 |
|------|------|---------|---------|
| new-api | new-api:custom | always | docker commit → /backup/ |
| newapi-redis | redis:7-alpine | always | redis-cli BGSAVE → /backup/ |
| newapi-mysql | mysql:8.0 | always | mysqldump → /backup/ |

## 备份频率
- MySQL: 每日03:00 mysqldump
- Redis: 每日03:30 BGSAVE+cp
- Docker镜像: 每周日docker commit

## 恢复目标
- RPO(恢复点): 24小时
- RTO(恢复时间): 30分钟
