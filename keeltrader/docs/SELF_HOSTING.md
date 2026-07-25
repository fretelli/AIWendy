# 自托管（Docker Compose）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

## 前置条件

- Docker Desktop 或 Docker Engine（含 Docker Compose v2）
- 至少 4 GB 可用内存和持久化磁盘空间

自托管统一使用 `docker-compose.selfhost.yml`，默认自带独立 PostgreSQL/pgvector、Redis、API、Web 和两个 Worker，且不连接任何维护者私有基础设施。维护者的生产域名、宿主机挂载、反向代理和发布凭据不在本仓库中。

## 快速开始

1. 复制环境变量：

   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env`，至少设置：

   - `POSTGRES_PASSWORD`
   - `JWT_SECRET`（建议 >= 32 位）
   - `ENCRYPTION_KEY`（建议 >= 32 位，用于加密 BYOK/MCP 凭据）
   - `NEXTAUTH_SECRET`
   - 模型密钥在 `/agent` 的 BYOK 设置中由每个用户单独配置

3. 启动服务：

   ```bash
   docker compose -f docker-compose.selfhost.yml up -d --build
   ```

API 默认通过 `KEELTRADER_RUN_MIGRATIONS=1` 在启动前运行 Alembic。只有在外部发布流程已经独立完成迁移时，才将其设为 `0`。

KeelTrader 默认不连接 Research Cloud。管理员可显式设置 `RESEARCH_CLOUD_ENABLED=1` 和 `RESEARCH_CLOUD_BASE_URL`，之后仍需每位用户通过 `/agent` 的“云研报”设置完成设备授权。连接器只发送检索词、公司筛选和报告 ID；本地文档、持仓、交易、模型密钥和决策日志不会上传。

## Research Agent、BYOK 与 MCP

- 运行 `alembic upgrade head` 创建 `agent_platform_*` 表。
- `/agent` 是唯一的 Agent 工作台和 API 入口。
- 每位用户必须添加自己的 OpenAI-compatible 或 Anthropic BYOK；自托管镜像不附带运营方 Token。
- BYOK 和 MCP Bearer Token 使用 `ENCRYPTION_KEY` 加密，仅在实际请求时解密。
- MCP 默认只接受公网 HTTPS，阻止 loopback、私网和云元数据地址；工具必须逐项授权。
- 定时研究由 `agent-platform-worker` 执行，只能使用永久授权工具。
- 任务级及每日 Token/费用硬上限耗尽时自动暂停。
- Agent 工具集不包含下单、撤单、交易同步、Ghost Trade 或代码执行。

## 登录

默认配置要求登录：`KEELTRADER_AUTH_REQUIRED=1`。

仅本地开发可以显式关闭登录：

```bash
KEELTRADER_AUTH_REQUIRED=0
```

仓库不提供启动时自动创建用户或测试账号的入口。首次用户通过注册 API 或网页注册流程创建。

## 常用命令

- 查看状态：`docker compose -f docker-compose.selfhost.yml ps`
- 跟踪日志：`docker compose -f docker-compose.selfhost.yml logs -f web api`
- 停止：`docker compose -f docker-compose.selfhost.yml down`
- 进入 API 容器：`docker compose -f docker-compose.selfhost.yml exec api sh`
- 验证构建但不部署：`./build.sh`
- 构建镜像：`./build.sh`
- 一次性冷启动验收：`scripts/selfhost-smoke.sh`

## 健康检查

- Web：`http://localhost:3000`
- Web health：`http://localhost:3000/api/health`
- API readiness：`docker compose -f docker-compose.selfhost.yml exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready').status)"`

---

<a id="en"></a>
## English

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose v2
- At least 4 GB of available memory and persistent disk space

Use `docker-compose.selfhost.yml` for every self-hosted deployment. It includes isolated PostgreSQL/pgvector, Redis, API, Web, and both workers and does not connect to maintainer-operated infrastructure by default. Maintainer domains, host mounts, reverse proxies, and release credentials are not stored in this repository.

## Quick Start

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set at least:

   - `POSTGRES_PASSWORD`
   - `JWT_SECRET` (recommended: >= 32 chars)
   - `ENCRYPTION_KEY` (recommended: >= 32 chars; encrypts BYOK/MCP credentials)
   - `NEXTAUTH_SECRET`
   - Each user configures model credentials through BYOK settings in `/agent`

3. Start services:

   ```bash
   docker compose -f docker-compose.selfhost.yml up -d --build
   ```

The API defaults to `KEELTRADER_RUN_MIGRATIONS=1` and runs Alembic before startup. Set it to `0` only when an external release process has already completed migrations.

KeelTrader does not connect to Research Cloud by default. An administrator may explicitly set `RESEARCH_CLOUD_ENABLED=1` and `RESEARCH_CLOUD_BASE_URL`; each user must still complete device authorization in the `/agent` “Cloud Research” settings. The connector sends only search terms, company filters, and report IDs. Local documents, positions, trades, model credentials, and decision journals are never uploaded.

## Research Agent, BYOK, and MCP

- Run `alembic upgrade head` to create the `agent_platform_*` tables.
- `/agent` is the only Agent workspace and API entry point.
- Each user adds an OpenAI-compatible or Anthropic BYOK profile. Self-hosted images contain no operator model token.
- BYOK and MCP bearer tokens are encrypted with `ENCRYPTION_KEY` and decrypted only for the selected request.
- User MCP accepts public HTTPS by default and blocks loopback, private networks, and cloud metadata destinations. Tools are approved individually.
- Scheduled research runs in `agent-platform-worker` and may use only permanently approved tools.
- Per-run and daily token/cost limits pause work when exhausted.
- No order placement, cancellation, trade sync, ghost-trade, or arbitrary-code tool is registered.

## Authentication

Authentication is required by default: `KEELTRADER_AUTH_REQUIRED=1`.

For local development only, you may explicitly disable login:

```bash
KEELTRADER_AUTH_REQUIRED=0
```

The repository has no startup path that auto-creates users or test accounts. Create the first user through the registration API or Web registration flow.

## Common Commands

- Status: `docker compose -f docker-compose.selfhost.yml ps`
- Tail logs: `docker compose -f docker-compose.selfhost.yml logs -f web api`
- Stop: `docker compose -f docker-compose.selfhost.yml down`
- Shell into API: `docker compose -f docker-compose.selfhost.yml exec api sh`
- Validate builds without deploy: `./build.sh`
- Build images: `./build.sh`
- Disposable clean-room smoke: `scripts/selfhost-smoke.sh`

## Health Checks

- Web: `http://localhost:3000`
- Web health: `http://localhost:3000/api/health`
- API readiness: `docker compose -f docker-compose.selfhost.yml exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready').status)"`
