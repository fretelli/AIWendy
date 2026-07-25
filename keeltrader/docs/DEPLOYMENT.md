# 部署与运行

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

## 支持的拓扑

KeelTrader 通过 `docker-compose.selfhost.yml` 运行以下应用组件：

- `web`：Next.js 前端
- `api`：FastAPI 后端
- `agent-platform-worker`：Agent Platform 心跳和后台任务
- `opportunity-worker`：跨资产机会快照后台物化

默认 Compose 同时提供 PostgreSQL/pgvector 和 Redis，也允许高级运维者通过自己的私有编排替换它们。完整首次启动流程见 [SELF_HOSTING.md](SELF_HOSTING.md)。

## 必要环境变量

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`
- 用户在 `/agent` 中配置的 BYOK 模型密钥
- `KEELTRADER_AUTH_REQUIRED=1`（公网/生产必须开启）

## 验证与启动

验证构建：

```bash
./build.sh
```

启动应用：

```bash
docker compose -f docker-compose.selfhost.yml up -d --build
docker compose -f docker-compose.selfhost.yml exec -T api alembic upgrade head
```

正式 tag 会通过 GitHub Actions 发布 API/Web GHCR 镜像、SBOM、provenance 和 GitHub Release。具体生产主机、域名、反向代理、凭据和回滚编排必须由部署者在自己的私有基础设施仓库中管理。

## 健康检查

- Web：`GET /api/health`
- API：`GET /api/health`
- API liveness：`GET /api/health/live`
- Agent Platform：`GET /api/v1/agent/health`

---

<a id="en"></a>
## English

## Supported Topology

KeelTrader runs these application components through `docker-compose.selfhost.yml`:

- `web`: Next.js frontend
- `api`: FastAPI backend
- `agent-platform-worker`: Agent Platform heartbeat and background tasks
- `opportunity-worker`: background materialization of cross-asset opportunity snapshots

The default Compose stack also provides PostgreSQL/pgvector and Redis. Advanced operators may replace them in their own private orchestration. See [SELF_HOSTING.md](SELF_HOSTING.md) for the complete first-run workflow.

## Required Environment Variables

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`
- User-scoped BYOK model credentials configured in `/agent`
- `KEELTRADER_AUTH_REQUIRED=1` for public/production deployments

## Validate And Start

Validate builds:

```bash
./build.sh
```

Start the application:

```bash
docker compose -f docker-compose.selfhost.yml up -d --build
docker compose -f docker-compose.selfhost.yml exec -T api alembic upgrade head
```

Version tags publish API/Web GHCR images, SBOMs, provenance, and a GitHub Release. Production hosts, domains, reverse proxies, credentials, and rollback orchestration belong in each operator's private infrastructure repository.

## Health Checks

- Web: `GET /api/health`
- API: `GET /api/health`
- API liveness: `GET /api/health/live`
- Agent Platform: `GET /api/v1/agent/health`
