# AgentProject

面向扫地机器人场景的智能客服系统，提供基于大模型的问答、RAG 知识检索、用户长期记忆、外部使用数据查询、认证鉴权、会话持久化，以及可直接交付的前后端一体化工作台。

该项目当前采用以下技术组合：

- 后端：FastAPI
- 智能体：LangChain Agent
- 模型：阿里云通义千问 ChatTongyi
- 向量库：Chroma
- 前端：Vue 3 + Vite + Pinia + Vue Router
- 数据库：PostgreSQL
- 异步任务：Celery + Redis
- 部署方式：本地开发、Docker Compose、生产编排

## 1. 项目价值

这个项目是一个具备企业交付基础能力的智能客服工程骨架，重点覆盖以下能力：

- 业务问答：支持通用客服问答与业务引导。
- RAG 检索：从本地知识库中召回文档并总结回答。
- 用户长期记忆：按用户维度保存问答摘要、偏好、事实和画像。
- 外部数据融合：按用户 ID 和年月读取外部 CSV 使用记录。
- 会话管理：支持新建会话、历史会话查询、会话删除与恢复上下文。
- 鉴权体系：支持注册、登录、Cookie 鉴权、会话隔离。
- 数据持久化：用户与会话写入 PostgreSQL。
- 异步任务：使用 Celery 承担会话异步保存、归档、清理、备份。
- 前后端联动：前端提供登录页、工作台、历史页，后端提供 REST API 与流式回复接口。

## 2. 系统架构

```text
Browser
	│
	├─ Vue 3 Frontend
	│    ├─ 登录/注册
	│    ├─ 聊天工作台
	│    └─ 历史会话
	│
	▼
FastAPI Backend
	├─ /api/auth/*
	├─ /api/chat
	├─ /api/chat/stream
	├─ /api/session/*
	└─ /api/sessions
	│
	├─ ReactAgent
	│    ├─ Tool 调用
	│    ├─ Prompt 组装
	│    ├─ 长期记忆检索
	│    └─ RAG 摘要生成
	│
	├─ PostgreSQL
	│    ├─ users
	│    └─ sessions
	│
	├─ Chroma
	│    └─ 本地知识库向量索引
	│
	└─ Redis + Celery
			 ├─ 异步保存会话
			 ├─ 归档过期会话
			 ├─ 清理已删除会话
			 └─ 数据备份
```

## 3. 核心能力

### 3.1 智能体能力

- 使用 LangChain Agent 组织工具调用。
- 工具包含天气、定位、当前月份、用户 ID、外部使用记录、RAG 检索等。
- 对简单闲聊类问题走直连模型路径，降低不必要的工具调用开销。
- 对报告、记录、月份、参考资料等强业务问题走工具链路。

### 3.2 RAG 能力

- 知识源位于 data 目录，支持 txt、pdf。
- 通过 Chroma 持久化向量索引到 chroma_db。
- 基于 md5.text 做增量去重，避免重复入库。
- 检索后结合模板提示词进行总结回答。

### 3.3 用户记忆能力

- 长期记忆按用户维度存储。
- 记忆类型包括 qa_summary、preference、fact、profile。
- 回答前会按 query 检索相关记忆并拼接到系统上下文中。

### 3.4 会话与认证能力

- 注册、登录、退出登录、获取当前登录用户。
- 会话按用户隔离，用户不能访问他人的 session。
- 支持普通问答接口和流式 SSE 输出接口。
- 会话在内存中即时可用，同时异步持久化到 PostgreSQL。

## 4. 技术栈

### 4.1 后端

- FastAPI
- Uvicorn
- LangChain
- LangGraph 生态依赖
- SQLAlchemy
- Celery
- Redis
- PostgreSQL
- ChromaDB

### 4.2 前端

- Vue 3
- TypeScript
- Pinia
- Vue Router
- Vite
- Nginx

### 4.3 模型与外部服务

- 通义千问：聊天模型
- DashScope Embeddings：向量化
- 高德地图：IP 定位与天气查询

## 5. 目录结构

```text
AgentProject/
├─ agent/                    Agent 逻辑、工具与中间件
├─ chroma_db/                Chroma 向量库存储目录
├─ config/                   YAML 配置
├─ data/                     知识库文本与外部业务数据
├─ frontend/                 Vue 3 前端项目
├─ logs/                     运行日志
├─ model/                    模型工厂
├─ prompts/                  系统提示词与 RAG 提示词
├─ rag/                      RAG、向量库、长期记忆相关逻辑
├─ scripts/                  初始化、备份、压测脚本
├─ tasks/                    Celery 异步任务
├─ utils/                    配置、日志、鉴权、存储等基础设施
├─ Dockerfile                后端镜像构建文件
├─ docker-compose.yml        前后端一体化 Docker 编排
├─ docker-compose.production.yml
├─ main.py                   FastAPI 入口
└─ README.md
```

## 6. 运行环境要求

推荐环境：

- Python 3.11 或 3.12
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker / Docker Compose（如使用容器部署）

## 7. 配置说明

### 7.1 环境变量

项目已提供 .env.example，可作为本地或部署环境变量模板。

建议至少配置以下变量：

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_NAME=agent_db
DATABASE_URL=postgresql://postgres:your_secure_password@localhost:5432/agent_db

AUTH_SECRET=replace-with-a-long-random-secret
AUTH_COOKIE_SECURE=false

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER=redis://localhost:6379/0
CELERY_BACKEND=redis://localhost:6379/0

DASHSCOPE_API_KEY=your_dashscope_api_key

SESSION_EXPIRE_DAYS=30
SESSION_ARCHIVE_DAYS=90
BACKUP_DIR=./backups
LOG_LEVEL=INFO
```

### 7.2 YAML 配置

配置文件位于 config 目录，当前主要包括：

- config/rag.yaml：模型名、向量化模型名
- config/chroma.yaml：向量库目录、chunk 策略、知识库目录
- config/agent.yaml：外部数据路径
- config/prompts.yaml：提示词文件路径
- config/map.yaml：地图服务配置

### 7.3 安全建议

当前项目中部分第三方配置来自 YAML 文件。生产环境建议统一收敛到环境变量、容器 Secret 或密钥管理服务，不建议把真实密钥直接保存在仓库配置文件中。

## 8. 本地开发启动

### 8.1 安装 Python 依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 8.2 准备环境变量

```bash
cp .env.example .env
```

根据实际环境补充以下内容：

- PostgreSQL 连接信息
- Redis 地址
- DASHSCOPE_API_KEY
- AUTH_SECRET

### 8.3 初始化知识库

首次导入知识库时执行：

```bash
python rag/vector_store.py
```

说明：

- 会扫描 data 目录下允许的知识文件类型。
- 对 txt、pdf 文档进行切分、向量化和入库。
- 已处理文件通过 md5.text 去重。

### 8.4 启动后端

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

默认地址：

- API 根服务健康检查：http://127.0.0.1:8000/health
- SSE 流式接口：http://127.0.0.1:8000/api/chat/stream

### 8.5 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

- http://127.0.0.1:5173

本地跨域白名单默认允许：

- http://127.0.0.1:5173
- http://localhost:5173

如需额外前端域名，可通过 FRONTEND_ORIGINS 环境变量覆盖。

### 8.6 启动异步任务组件

如果你希望本地完整验证会话异步保存、归档、备份链路，还需要启动 Redis、Celery Worker 和 Celery Beat。

如果本机没有安装 Redis，可直接用 Docker 先启动基础设施：

```bash
docker compose -f docker-compose.production.yml up -d postgres redis
```

如果已经激活 `.venv` 但 shell 里找不到 `celery` 命令，优先使用 `python -m celery`。

```bash
python -m celery -A tasks.celery_tasks worker -l info
python -m celery -A tasks.celery_tasks beat -l info
```

说明：

- FastAPI 启动时会挂载 Celery app，用于共享异步任务配置。
- Celery Beat 调度表定义在 `tasks/celery_tasks.py`，由 Beat 进程自身加载。
- `session_id` 现支持最长 128 个字符；已有数据库会在应用启动或执行 `python scripts/init_db.py` 时自动扩容列定义。

## 9. Docker 启动

### 9.1 开发型一体化编排

项目根目录执行：

```bash
docker compose up --build
```

该编排默认包含：

- postgres
- backend
- frontend

访问地址：

- 前端：http://localhost
- 健康检查：http://localhost/health
- API 入口：http://localhost/api/chat

停止服务：

```bash
docker compose down
```

后台启动：

```bash
docker compose up -d --build
```

### 9.2 生产型编排

项目额外提供 docker-compose.production.yml，包含：

- PostgreSQL
- Redis
- FastAPI
- Celery Worker
- Celery Beat

启动命令：

```bash
docker compose -f docker-compose.production.yml up -d --build postgres redis fastapi celery celery_beat
```

查看状态：

```bash
docker compose -f docker-compose.production.yml ps
```

如只需本地验证 Redis/PostgreSQL 基础设施，可先执行：

```bash
docker compose -f docker-compose.production.yml up -d postgres redis
```

## 10. API 概览

### 10.1 系统接口

- GET /health：健康检查

### 10.2 认证接口

- POST /api/auth/register：注册并登录
- POST /api/auth/login：登录
- POST /api/auth/logout：退出登录
- GET /api/auth/me：获取当前用户信息

### 10.3 聊天接口

- POST /api/chat：非流式问答
- GET /api/chat/stream：流式问答，基于 text/event-stream

### 10.4 会话接口

- GET /api/sessions：获取当前用户全部会话摘要
- GET /api/session/{session_id}：获取指定会话详情
- DELETE /api/session/{session_id}：删除指定会话

## 11. 前端页面说明

前端工作台包含三个主要页面：

- /auth：登录与注册页
- /：主工作台，包含会话侧边栏、消息区、输入区
- /history：历史会话页

前端 API 地址由 frontend/src/constants/api.ts 中的 VITE_API_BASE_URL 控制；在容器中，Nginx 会将 /api 和 /health 代理到后端服务。

## 12. 数据与存储设计

### 12.1 PostgreSQL

主要承载以下数据：

- 用户认证信息 users
- 会话记录 sessions

会话数据字段包括：

- session_id
- user_id
- messages
- created_at
- updated_at
- status

### 12.2 Chroma

用于存储知识库向量索引，默认目录为 chroma_db。

### 12.3 外部业务数据

外部记录文件位于 data/external/records.csv，通过用户 ID + 年月检索，供报告类问题或数据查询类问题调用。

## 13. 定时任务与备份

系统启动后会注册以下计划任务：

- 凌晨 2:00：归档过期会话
- 凌晨 3:00：清理已删除会话
- 凌晨 4:00：数据库备份

手动备份命令：

```bash
bash scripts/backup.sh backup
```

恢复示例：

```bash
bash scripts/backup.sh restore ./backups/your_backup.sql.gz
```

## 14. 日志与可观测性

- 日志默认写入 logs 目录。
- 控制台输出 INFO 级别，文件保留 DEBUG 级别。
- .env.example 中包含 ENABLE_METRICS 和 METRICS_PORT 配置项，可作为后续 Prometheus 暴露的基础配置。

## 15. 测试与验证建议

建议至少覆盖以下验证场景：

- 用户注册、登录、退出登录流程
- 非流式问答与流式问答
- 同用户多会话切换
- 跨用户会话隔离
- 外部数据查询是否按年月命中
- 知识库检索与 RAG 输出质量
- PostgreSQL 持久化是否成功
- Celery 异步保存和重试机制是否正常

项目中提供了压测脚本，可按需查看：

- scripts/benchmark_chat.py

## 16. 工程化改进建议

如果要进一步向企业级交付靠拢，建议优先补齐以下事项：

- 增加自动化测试：单元测试、接口测试、E2E 测试
- 引入统一配置管理与 Secret 管理
- 为 FastAPI 增加 OpenAPI 使用说明与接口示例
- 将日志、指标、追踪接入统一观测平台
- 增加 CI/CD：Lint、Test、Build、Deploy 流水线
- 完善权限模型、审计日志和风控策略
- 为 Chroma、PostgreSQL、Redis 制定数据备份与恢复演练流程

## 17. 常见问题

### 17.1 无法连接数据库

排查项：

- PostgreSQL 是否启动
- DATABASE_URL 是否正确
- 数据库用户和密码是否匹配
- Docker 网络或本地端口是否冲突

### 17.2 知识库没有命中结果

排查项：

- 是否执行过 python rag/vector_store.py
- data 目录下是否存在 txt/pdf 文件
- md5.text 是否导致文件被判定为已导入
- DASHSCOPE_API_KEY 是否有效

### 17.3 流式回复没有输出

排查项：

- 前端是否使用 SSE 正确消费 /api/chat/stream
- 反向代理是否允许 text/event-stream
- 浏览器与后端间是否存在跨域或 Cookie 问题

### 17.4 登录成功但接口仍返回 401

排查项：

- AUTH_SECRET 是否一致
- Cookie 是否成功写入
- AUTH_COOKIE_SECURE 在本地开发环境是否错误设置为 true

## 18. 参考文档

项目内已存在以下补充文档：

- DEPLOY_DOCKER.md
- PRODUCTION_DEPLOYMENT.md

