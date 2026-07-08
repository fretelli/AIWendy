# 自托管（Docker Compose）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

## 前置条件

- Docker Desktop 或 Docker Engine（含 Docker Compose v2）
- 可访问的 PostgreSQL（推荐 pgvector）和 Redis

当前 `docker-compose.yml` 只编排 `api`、`web`、`agent-engine`，不内置 PostgreSQL/Redis。生产环境使用外部数据库与共享 Redis。

## 快速开始

1. 复制环境变量：

   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env`，至少设置：

   - `DATABASE_URL`
   - `REDIS_URL`
   - `JWT_SECRET`（建议 >= 32 位）
   - `NEXTAUTH_SECRET`
   - `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`（需要 AI 能力时）

3. 启动服务：

   ```bash
   docker compose up -d api web agent-engine
   ```

4. 首次部署或升级后运行迁移：

   ```bash
   docker compose exec -T api alembic upgrade head
   ```

## 登录与测试账号

默认配置要求登录：`KEELTRADER_AUTH_REQUIRED=1`。

仅本地开发可以显式关闭登录：

```bash
KEELTRADER_AUTH_REQUIRED=0
```

测试账号初始化默认关闭。如需本地创建测试账号：

```bash
export KEELTRADER_DEV_USER_PASSWORD='choose-a-local-dev-password'
export KEELTRADER_DEV_ADMIN_PASSWORD='choose-a-local-admin-password'
docker compose exec -T api python scripts/init_user_simple.py
```

生产环境不要启用 `KEELTRADER_AUTO_INIT_TEST_USERS`。

## 常用命令

- 查看状态：`docker compose ps`
- 跟踪日志：`docker compose logs -f web api agent-engine`
- 停止：`docker compose down`
- 进入 API 容器：`docker compose exec api sh`
- 验证构建但不部署：`./build.sh`
- 发布 Web：`scripts/deploy.sh web`
- 发布 API + agent-engine：`scripts/deploy.sh api`

## 健康检查

- Web：`http://localhost:3000`
- Web health：`http://localhost:3000/api/health`
- API health：`docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').status)"`

---

<a id="en"></a>
## English

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose v2
- Reachable PostgreSQL (pgvector recommended) and Redis

The current `docker-compose.yml` only orchestrates `api`, `web`, and `agent-engine`. PostgreSQL and Redis are external services.

## Quick Start

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set at least:

   - `DATABASE_URL`
   - `REDIS_URL`
   - `JWT_SECRET` (recommended: >= 32 chars)
   - `NEXTAUTH_SECRET`
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` when AI features are needed

3. Start services:

   ```bash
   docker compose up -d api web agent-engine
   ```

4. Run migrations after first deploy or upgrades:

   ```bash
   docker compose exec -T api alembic upgrade head
   ```

## Authentication and Test Users

Authentication is required by default: `KEELTRADER_AUTH_REQUIRED=1`.

For local development only, you may explicitly disable login:

```bash
KEELTRADER_AUTH_REQUIRED=0
```

Test account initialization is disabled by default. To create local test users:

```bash
export KEELTRADER_DEV_USER_PASSWORD='choose-a-local-dev-password'
export KEELTRADER_DEV_ADMIN_PASSWORD='choose-a-local-admin-password'
docker compose exec -T api python scripts/init_user_simple.py
```

Do not enable `KEELTRADER_AUTO_INIT_TEST_USERS` in production.

## Common Commands

- Status: `docker compose ps`
- Tail logs: `docker compose logs -f web api agent-engine`
- Stop: `docker compose down`
- Shell into API: `docker compose exec api sh`
- Validate builds without deploy: `./build.sh`
- Release Web: `scripts/deploy.sh web`
- Release API + agent-engine: `scripts/deploy.sh api`

## Health Checks

- Web: `http://localhost:3000`
- Web health: `http://localhost:3000/api/health`
- API health: `docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').status)"`
