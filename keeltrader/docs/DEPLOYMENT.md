# 部署与运行

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

## 支持的拓扑

KeelTrader 通过 Docker Compose 运行以下应用组件：

- `web`：Next.js 前端
- `api`：FastAPI 后端
- `agent-engine`：AgentOS 心跳和后台任务

PostgreSQL 和 Redis 通过环境变量作为外部服务接入。完整首次启动流程见 [SELF_HOSTING.md](SELF_HOSTING.md)。

## 必要环境变量

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`（按需）
- `KEELTRADER_AUTH_REQUIRED=1`（公网/生产必须开启）

## 验证与启动

验证构建：

```bash
./build.sh
```

启动应用：

```bash
docker compose up -d api web agent-engine
docker compose exec -T api alembic upgrade head
```

公开文档不承诺特定主机、反向代理或镜像发布流程；运维者应在私有基础设施配置中管理这些细节。

## 健康检查

- Web：`GET /api/health`
- API：`GET /api/health`
- API liveness：`GET /api/health/live`
- AgentOS：`GET /api/v1/agentos/health`

---

<a id="en"></a>
## English

## Supported Topology

KeelTrader runs these application components through Docker Compose:

- `web`: Next.js frontend
- `api`: FastAPI backend
- `agent-engine`: AgentOS heartbeat and background tasks

PostgreSQL and Redis are external services configured through environment variables. See [SELF_HOSTING.md](SELF_HOSTING.md) for the complete first-run workflow.

## Required Environment Variables

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` as needed
- `KEELTRADER_AUTH_REQUIRED=1` for public/production deployments

## Validate And Start

Validate builds:

```bash
./build.sh
```

Start the application:

```bash
docker compose up -d api web agent-engine
docker compose exec -T api alembic upgrade head
```

Public documentation does not define a specific host, reverse proxy, or image-release pipeline. Operators should manage those details in private infrastructure configuration.

## Health Checks

- Web: `GET /api/health`
- API: `GET /api/health`
- API liveness: `GET /api/health/live`
- AgentOS: `GET /api/v1/agentos/health`
