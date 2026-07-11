# 自托管（Docker Compose）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

## 前置条件

- Docker Desktop 或 Docker Engine（含 Docker Compose v2）
- 约 1 GB 可用内存和持久化磁盘空间

私有部署使用 `docker-compose.selfhost.yml`，默认自带独立 PostgreSQL/pgvector 和 Redis，且不连接 KeelTrader 官方服务器。仓库根目录的 `docker-compose.yml` 是官方托管环境编排，不用于第三方私有部署。

## 快速开始

1. 复制环境变量：

   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env`，至少设置：

   - `POSTGRES_PASSWORD`
   - `JWT_SECRET`（建议 >= 32 位）
   - `NEXTAUTH_SECRET`
   - 模型密钥在 `/agent` 的 BYOK 设置中由每个用户单独配置

3. 启动服务：

   ```bash
   docker compose -f docker-compose.selfhost.yml up -d --build
   ```

4. 首次部署或升级后运行迁移：

   ```bash
   docker compose -f docker-compose.selfhost.yml exec -T api alembic upgrade head
   ```

默认 `RESEARCH_CLOUD_ENABLED=0`，Web/API 不会请求任何 `joyeeassets.com` 域名。只有管理员显式开启、且具体用户完成设备授权后，才会发送研报查询词和公司筛选到 Research Cloud；本地文档、持仓、交易与决策日志不会上传。

## Agent 平台、BYOK 与 MCP

- 运行 `alembic upgrade head` 创建 `agent_platform_*` 表。
- `/agent` 是唯一的 Agent 工作台和 API 入口。
- 每位用户必须添加自己的 OpenAI-compatible 或 Anthropic BYOK；自托管镜像不附带运营方 Token。
- BYOK 和 MCP Bearer Token 使用 `ENCRYPTION_KEY` 加密，仅在实际请求时解密。
- MCP 默认只接受公网 HTTPS，阻止 loopback、私网和云元数据地址；工具必须逐项授权。
- 定时研究由 `agent-platform-worker` 执行，只能使用永久授权工具。
- 任务级及每日 Token/费用硬上限耗尽时自动暂停。
- Agent 工具集不包含下单、撤单、交易同步、Ghost Trade 或代码执行。

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
docker compose -f docker-compose.selfhost.yml exec -T api python scripts/init_user_simple.py
```

生产环境不要启用 `KEELTRADER_AUTO_INIT_TEST_USERS`。

## 常用命令

- 查看状态：`docker compose -f docker-compose.selfhost.yml ps`
- 跟踪日志：`docker compose -f docker-compose.selfhost.yml logs -f web api`
- 停止：`docker compose -f docker-compose.selfhost.yml down`
- 进入 API 容器：`docker compose -f docker-compose.selfhost.yml exec api sh`
- 验证构建但不部署：`./build.sh`
- 发布 Web：`scripts/deploy.sh web`
- 发布 API + Agent Platform Worker：`scripts/deploy.sh api`

## 健康检查

- Web：`http://localhost:3000`
- Web health：`http://localhost:3000/api/health`
- API health：`docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').status)"`

---

<a id="en"></a>
## English

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose v2
- About 1 GB of available memory and persistent disk space

Use `docker-compose.selfhost.yml` for private deployments. It includes isolated PostgreSQL/pgvector and Redis services and does not connect to KeelTrader-operated services by default. The root `docker-compose.yml` is the managed production deployment definition.

## Quick Start

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set at least:

   - `POSTGRES_PASSWORD`
   - `JWT_SECRET` (recommended: >= 32 chars)
   - `NEXTAUTH_SECRET`
   - Each user configures model credentials through BYOK settings in `/agent`

3. Start services:

   ```bash
   docker compose -f docker-compose.selfhost.yml up -d --build
   ```

4. Run migrations after first deploy or upgrades:

   ```bash
   docker compose -f docker-compose.selfhost.yml exec -T api alembic upgrade head
   ```

`RESEARCH_CLOUD_ENABLED=0` is the default. No request is sent to a `joyeeassets.com` domain unless an administrator explicitly enables Research Cloud and an individual user completes device authorization. Local documents, positions, trades, and decision journals are never uploaded.

## Agent Platform, BYOK, and MCP

- Run `alembic upgrade head` to create the `agent_platform_*` tables.
- `/agent` is the only Agent workspace and API entry point.
- Each user adds an OpenAI-compatible or Anthropic BYOK profile. Self-hosted images contain no operator model token.
- BYOK and MCP bearer tokens are encrypted with `ENCRYPTION_KEY` and decrypted only for the selected request.
- User MCP accepts public HTTPS by default and blocks loopback, private networks, and cloud metadata destinations. Tools are approved individually.
- Scheduled research runs in `agent-platform-worker` and may use only permanently approved tools.
- Per-run and daily token/cost limits pause work when exhausted.
- No order placement, cancellation, trade sync, ghost-trade, or arbitrary-code tool is registered.

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

- Status: `docker compose -f docker-compose.selfhost.yml ps`
- Tail logs: `docker compose -f docker-compose.selfhost.yml logs -f web api`
- Stop: `docker compose -f docker-compose.selfhost.yml down`
- Shell into API: `docker compose -f docker-compose.selfhost.yml exec api sh`
- Validate builds without deploy: `./build.sh`
- Release Web: `scripts/deploy.sh web`
- Release API + Agent Platform Worker: `scripts/deploy.sh api`

## Health Checks

- Web: `http://localhost:3000`
- Web health: `http://localhost:3000/api/health`
- API health: `docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').status)"`
