# 部署与发布

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

## 当前生产形态

KeelTrader 当前按本机 Docker Compose 部署：

- `web`：Next.js 前端
- `api`：FastAPI 后端
- `agent-engine`：复用 API 镜像运行 AgentOS 心跳/任务
- PostgreSQL 与 Redis：外部服务，通过 `.env` 中的 `DATABASE_URL` / `REDIS_URL` 接入

旧的 Vercel/Railway/Fly.io 路径已停用。发布使用 overlay 镜像，默认复用已有 base image，避免不必要的完整依赖层 rebuild。

## 必要环境变量

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`（至少一个，按需）
- `KEELTRADER_AUTH_REQUIRED=1`（公网/生产必须保持开启）

## 发布命令

验证构建但不部署：

```bash
./build.sh
```

发布 Web：

```bash
scripts/deploy.sh web
```

发布 API + agent-engine：

```bash
scripts/deploy.sh api
```

只跑 smoke：

```bash
scripts/deploy.sh web --smoke-only
scripts/deploy.sh api --smoke-only
```

## 迁移

首次部署或升级后运行：

```bash
docker compose exec -T api alembic upgrade head
```

## 健康检查

- Web：`GET /api/health`
- API：`GET /api/health`
- API liveness：`GET /api/health/live`
- AgentOS：`GET /api/v1/agentos/health`

---

<a id="en"></a>
## English

## Current Production Shape

KeelTrader currently deploys on a local Docker Compose host:

- `web`: Next.js frontend
- `api`: FastAPI backend
- `agent-engine`: reuses the API image for AgentOS heartbeat/tasks
- PostgreSQL and Redis: external services configured through `DATABASE_URL` / `REDIS_URL`

The old Vercel/Railway/Fly.io path is disabled. Releases use overlay images and reuse existing base images by default to avoid unnecessary dependency-layer rebuilds.

## Required Environment Variables

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` as needed
- `KEELTRADER_AUTH_REQUIRED=1` for public/production deployments

## Release Commands

Validate builds without deploy:

```bash
./build.sh
```

Release Web:

```bash
scripts/deploy.sh web
```

Release API + agent-engine:

```bash
scripts/deploy.sh api
```

Smoke only:

```bash
scripts/deploy.sh web --smoke-only
scripts/deploy.sh api --smoke-only
```

## Migrations

After first deploy or upgrades:

```bash
docker compose exec -T api alembic upgrade head
```

## Health Checks

- Web: `GET /api/health`
- API: `GET /api/health`
- API liveness: `GET /api/health/live`
- AgentOS: `GET /api/v1/agentos/health`
