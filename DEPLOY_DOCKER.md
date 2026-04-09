# Docker 部署

## 1. 环境准备
在项目根目录准备 `.env` 文件：

```env
DASHSCOPE_API_KEY=你的密钥
DB_TYPE=postgresql
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_NAME=agent_db
DB_PORT=5432
AUTH_SECRET=replace-with-a-long-random-secret
AUTH_COOKIE_SECURE=false
```

## 2. 启动容器
在项目根目录执行：

```bash
docker compose up --build
```

## 3. 访问地址
- 前端：`http://localhost`
- 后端健康检查：`http://localhost/health`
- 后端 API：`http://localhost/api/chat`

## 4. 说明
- `backend` 运行 FastAPI，容器内端口 `8000`
- `postgres` 存储用户登录信息与会话数据
- `frontend` 使用 `Vue + Vite` 构建，最终由 `Nginx` 提供静态资源
- 前端通过 `Nginx` 反向代理 `/api` 和 `/health` 到后端服务
- Vue 路由使用 history 模式，已通过 `try_files` 做回退处理

## 5. 常用命令
停止：

```bash
docker compose down
```

后台启动：

```bash
docker compose up -d --build
```
