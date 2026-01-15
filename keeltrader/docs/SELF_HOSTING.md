# 自托管（Docker Compose）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

## 前置条件

- Docker Desktop（含 Docker Compose v2）

> Windows PowerShell 如果用 `Get-Content` 查看本文件出现乱码，建议用 `Get-Content -Encoding utf8`，或直接用编辑器/浏览器打开（GitHub 显示正常）。

## 快速开始

1. 复制环境变量：
   - PowerShell：`Copy-Item .env.example .env`
   - macOS/Linux：`cp .env.example .env`

2. 编辑 `.env`，至少设置：
   - `DB_PASSWORD`
   - `JWT_SECRET`（建议 ≥ 32 位）
   - `NEXTAUTH_SECRET`（建议）
   - `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`（需要 AI 能力时）

3. 启动服务（db + redis + api + web）：

   ```bash
   docker compose up -d --build
   ```

## 访客模式（免登录，默认）

默认配置为免登录体验：

- API：`.env` 中 `KEELTRADER_AUTH_REQUIRED=0`
- Web：会自动检测后端是否支持 guest（不再依赖前端开关）

验证方式（不带 token 直接访问）：

- `http://localhost:8000/api/v1/users/me` 应返回 `guest@local.aiwendy`

如果你想在公网/生产环境强制登录：

- 将 `.env` 设置为 `KEELTRADER_AUTH_REQUIRED=1` 并重启：`docker compose up -d --build`

## 可选：自动初始化数据库与测试账号

容器启动时可以自动执行初始化脚本（建议仅本地开发用）：

- `KEELTRADER_AUTO_INIT_DB=1`：自动初始化数据库结构（默认开启）
- `KEELTRADER_AUTO_INIT_TEST_USERS=1`：自动创建测试账号（默认关闭）

手动执行（可选）：

```bash
docker exec aiwendy-api python scripts/init_db_simple.py
docker exec aiwendy-api python scripts/init_user_simple.py
```

如果开启了 `KEELTRADER_AUTO_INIT_TEST_USERS=1`，测试账号为：

| Type | Email | Password | Access |
|------|-------|----------|--------|
| User | test@example.com | Test@1234 | Free |
| Admin | admin@aiwendy.com | Admin@123 | Elite + Admin |

## 访问地址

- Web：`http://localhost:3000`
- API 健康检查：`http://localhost:8000/api/health`
- API 文档：`http://localhost:8000/docs`

## 可选：后台任务（worker/beat）

默认不开启；需要时运行：

```bash
docker compose --profile workers up -d --build
```

## 常用命令

- 查看状态：`docker compose ps`
- 跟踪日志：`docker compose logs -f web api`
- 停止：`docker compose down`
- 停止并清空数据：`docker compose down -v`
- 进入 API 容器：`docker exec -it aiwendy-api sh`
- 进入数据库：`docker exec -it aiwendy-db psql -U aiwendy`

## 常见问题

### 仍然被要求登录/跳转到登录页

1. 先确认后端是否允许 guest：访问 `http://localhost:8000/api/v1/users/me`
2. 若返回 401：
   - 检查 `.env` 是否设置 `KEELTRADER_AUTH_REQUIRED=0`
   - 重新构建并启动：`docker compose up -d --build`
3. 若之前登录过，建议清理浏览器 LocalStorage 中的 `aiwendy_access_token` / `aiwendy_refresh_token` 后刷新

### “Network error: unable to reach the API server”

通常表示浏览器无法访问后端 API（API 未启动、`NEXT_PUBLIC_API_URL` 错误、或 web→api 代理未生效）：

- API：`http://localhost:8000/api/health`
- Web 代理：`http://localhost:3000/api/proxy/health`
- 服务状态：`docker compose ps`

如果 `Web 代理` 返回 `502`，通常是 Web 侧配置的 API 地址不可达：

- Web 跑在宿主机（`npm run dev`）：用 `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Web 跑在 Docker Compose：用 `NEXT_PUBLIC_API_URL=http://api:8000`（服务名）

---

<a id="en"></a>
## English

## Prerequisites

- Docker Desktop (with Docker Compose v2)

> If Windows PowerShell shows garbled characters when using `Get-Content`, try `Get-Content -Encoding utf8`, or open this file in your editor/browser (GitHub renders it correctly).

## Quick start

1. Copy env vars:
   - PowerShell: `Copy-Item .env.example .env`
   - macOS/Linux: `cp .env.example .env`

2. Edit `.env` and set at least:
   - `DB_PASSWORD`
   - `JWT_SECRET` (recommended: ≥ 32 chars)
   - `NEXTAUTH_SECRET` (recommended)
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (needed for AI features)

3. Start services (db + redis + api + web):

   ```bash
   docker compose up -d --build
   ```

## Guest mode (no login, default)

The default config enables a no-login experience:

- API: `KEELTRADER_AUTH_REQUIRED=0` in `.env`
- Web: auto-detects whether the backend supports guest (no longer relies on a front-end flag)

How to verify (call without a token):

- `http://localhost:8000/api/v1/users/me` should return `guest@local.aiwendy`

If you want to enforce login in public/production:

- Set `KEELTRADER_AUTH_REQUIRED=1` in `.env` and restart: `docker compose up -d --build`

## Optional: auto-init DB and test accounts

On container startup you can run init scripts automatically (recommended for local dev only):

- `KEELTRADER_AUTO_INIT_DB=1`: auto-initialize DB schema (enabled by default)
- `KEELTRADER_AUTO_INIT_TEST_USERS=1`: auto-create test accounts (disabled by default)

Manual run (optional):

```bash
docker exec aiwendy-api python scripts/init_db_simple.py
docker exec aiwendy-api python scripts/init_user_simple.py
```

If `KEELTRADER_AUTO_INIT_TEST_USERS=1` is enabled, default test accounts are:

| Type | Email | Password | Access |
|------|-------|----------|--------|
| User | test@example.com | Test@1234 | Free |
| Admin | admin@aiwendy.com | Admin@123 | Elite + Admin |

## URLs

- Web: `http://localhost:3000`
- API health: `http://localhost:8000/api/health`
- API docs: `http://localhost:8000/docs`

## Optional: background jobs (worker/beat)

Disabled by default; when needed:

```bash
docker compose --profile workers up -d --build
```

## Common commands

- Status: `docker compose ps`
- Tail logs: `docker compose logs -f web api`
- Stop: `docker compose down`
- Stop and wipe data: `docker compose down -v`
- Enter API container: `docker exec -it aiwendy-api sh`
- Enter DB: `docker exec -it aiwendy-db psql -U aiwendy`

## FAQ

### Still being asked to log in / redirected to login

1. Confirm guest is allowed by backend: visit `http://localhost:8000/api/v1/users/me`
2. If it returns 401:
   - Check `.env` has `KEELTRADER_AUTH_REQUIRED=0`
   - Rebuild and restart: `docker compose up -d --build`
3. If you logged in before, clear LocalStorage keys `aiwendy_access_token` / `aiwendy_refresh_token` and refresh

### “Network error: unable to reach the API server”

Usually means the browser cannot reach the API (API not running, wrong `NEXT_PUBLIC_API_URL`, or the web→api proxy is not working):

- API: `http://localhost:8000/api/health`
- Web proxy: `http://localhost:3000/api/proxy/health`
- Service status: `docker compose ps`

If `Web proxy` returns `502`, the API address configured on the web side is likely unreachable:

- When running Web on the host (`npm run dev`): use `NEXT_PUBLIC_API_URL=http://localhost:8000`
- When running Web in Docker Compose: use `NEXT_PUBLIC_API_URL=http://api:8000` (service name)
