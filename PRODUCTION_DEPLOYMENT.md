# 生产级部署指南

## 架构概览

```
┌─────────────────┐
│ FastAPI App     │ (3+ 实例，负载均衡)
└────────┬────────┘
         │
    ┌────┴─────────────┬──────────────┐
    ▼                  ▼              ▼
┌─────────┐      ┌─────────┐    ┌──────────┐
│PostgreSQL│      │  Redis  │    │  Chroma  │
│ 主从复制  │      │(缓存+队列)│    │（向量库）│
└─────────┘      └─────────┘    └──────────┘
    ▲                  ▲
    │                  │
┌───┴──────────────────┴──────┐
│   Celery Tasks + Beat       │
│ (异步保存/定时维护)          │
└────────────────────────────┘
```

## 快速开始（Docker）

### 1. 环境配置

```bash
# 复制并修改环境变量
cp .env.example .env

# 编辑 .env，填入实际的密码和 API Key
nano .env
```

### 2. 启动所有服务

```bash
# 使用生产级 Docker Compose
docker compose -f docker-compose.production.yml up -d --build postgres redis fastapi celery celery_beat prometheus grafana

# 验证所有服务启动成功
docker compose -f docker-compose.production.yml ps
```

### 3. 初始化数据库

```bash
# 进入 FastAPI 容器
docker compose -f docker-compose.production.yml exec fastapi bash

# 运行初始化脚本
python scripts/init_db.py
```

说明：

- `python scripts/init_db.py` 除创建表外，还会把已有 `sessions.session_id` 列自动扩容到 128 字符。
- 如果只想在本机验证 Redis/Celery 链路，可先用 Docker 起 `postgres` 和 `redis`，再在 `.venv` 内运行 FastAPI、Worker、Beat。

## 手动部署（物理服务器）

### 1. 前置依赖

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_db.py
```

### 2. 启动服务

```bash
# 终端 1: FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000

# 终端 2: Celery Worker
python -m celery -A tasks.celery_tasks worker -l info

# 终端 3: Celery Beat（定时任务）
python -m celery -A tasks.celery_tasks beat -l info
```

如需本机同时观测指标，建议附加以下环境变量：

```bash
export ENABLE_METRICS=true
export METRICS_PORT=8001
export CELERY_METRICS_PORT=8002
```

如果本机没有 Redis 服务：

```bash
docker compose -f docker-compose.production.yml up -d postgres redis
```

## 关键功能

### 短期记忆（会话历史）

- **存储位置**：PostgreSQL `sessions` 表
- **加载时机**：应用启动时加载 7 天内的会话
- **保存方式**：异步保存（Celery），同步备份
- **自动清理**：
  - 30 天后自动归档（`archived` 状态）
  - 90 天后永久删除

### 长期记忆

- **存储位置**：Chroma 向量库
- **类型**：`qa_summary`, `preference`, `fact`, `profile`
- **检索**：语义相似度检索（向量近似搜索）

### 定时任务

```crontab
# 凌晨 2:00 - 归档过期会话
0 2 * * * archive-expired-sessions

# 凌晨 3:00 - 清理已删除的会话
0 3 * * * cleanup-deleted-sessions

# 凌晨 4:00 - 备份数据库
0 4 * * * backup-sessions
```

## 监控 & 备份

### 查看监控指标

```bash
# FastAPI 指标
curl http://localhost:8001/metrics

# Celery Worker 指标
curl http://localhost:8002/metrics

# Prometheus UI
open http://localhost:9090

# Grafana UI
open http://localhost:3000
```

说明：

- Grafana 默认账号密码：`admin/admin`
- 预置数据源与仪表盘会在容器启动时自动导入
- 预置面板覆盖 HTTP 请求、数据库查询、会话存储错误和 Celery 任务指标

### 手动备份

```bash
# 备份数据库
bash scripts/backup.sh backup

# 恢复备份
bash scripts/backup.sh restore ./backups/postgresql_backup_20260408_120000.sql.gz
```

## 故障恢复

### 会话丢失

1. **检查 PostgreSQL 连接**
   ```bash
   psql -h localhost -U postgres -d agent_db -c "SELECT COUNT(*) FROM sessions WHERE status='active';"
   ```

2. **重载会话**
   - 重启 FastAPI：`docker-compose restart fastapi`
   - 应用启动时自动从 DB 加载最近 7 天的会话

3. **从备份恢复**
   ```bash
   bash scripts/backup.sh restore <backup_file>
   ```

### Celery 任务失败

1. **查看 Celery 日志**
   ```bash
   docker compose -f docker-compose.production.yml logs celery
   ```

2. **重启 Worker**
   ```bash
   docker compose -f docker-compose.production.yml restart celery
   ```

3. **手动重新保存会话**
   - Celery 自动重試 3 次，最终失败时会写入错误日志
   - 同步备份会保存会话，确保数据不丢失

## 生产最佳实践

### 高可用

- ✅ PostgreSQL 主从复制
  ```bash
  # 在从库上创建复制槽
  SELECT * FROM pg_create_physical_replication_slot('replica_1');
  ```

- ✅ Redis Sentinel 故障转移
  ```yaml
  # docker-compose.yml 中配置 Redis Sentinel
  ```

- ✅ FastAPI 多副本 + 负载均衡（Nginx）

### 性能优化

- ✅ 异步会话保存（避免阻塞用户請求）
- ✅ 会话缓存热身（启动加载 7 天内数据）
- ✅ 数据库索引优化（已配置 `idx_user_id_updated_at`）
- ✅ Redis 连接池（自动管理）

### 安全

- ✅ 环境变量存储敏感信息（不上傳 .env）
- ✅ 数据库软删除（status='deleted'，防止误删除）
- ✅ 定期备份（自动每天凌晨 4:00）
- ✅ 访问日志（用于审计）

## 故障排查

### 常见问题

**Q: "Failed to connect to database"**
- A: 检查 PostgreSQL 是否运行，验证 `DATABASE_URL` 配置

**Q: "Celery task timeout"**
- A: 增加任务超时时间，或优化慢查询

**Q: "Memory usage keeps growing"**
- A: 检查 Celery 任务是否有内存泄漏，考虑定期 worker 重启

## 监控 Checklist

- [ ] PostgreSQL 主从同步延迟 < 1s
- [ ] Redis 内存使用率 < 80%
- [ ] Celery 任务队列 depth < 1000
- [ ] API 响应时间 p95 < 5s
- [ ] 每日备份成功率 = 100%
- [ ] 会话数增长符合预期
