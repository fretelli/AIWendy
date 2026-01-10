# 自托管（Docker Compose）

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

- API：`.env` 中 `AIWENDY_AUTH_REQUIRED=0`
- Web：会自动检测后端是否支持 guest（不再依赖前端开关）

验证方式（不带 token 直接访问）：

- `http://localhost:8000/api/v1/users/me` 应返回 `guest@local.aiwendy`

如果你想在公网/生产环境强制登录：

- 将 `.env` 设置为 `AIWENDY_AUTH_REQUIRED=1` 并重启：`docker compose up -d --build`

## 可选：自动初始化数据库与测试账号

容器启动时可以自动执行初始化脚本（建议仅本地开发用）：

- `AIWENDY_AUTO_INIT_DB=1`：自动初始化数据库结构（默认开启）
- `AIWENDY_AUTO_INIT_TEST_USERS=1`：自动创建测试账号（默认关闭）

手动执行（可选）：

```bash
docker exec aiwendy-api python scripts/init_db_simple.py
docker exec aiwendy-api python scripts/init_user_simple.py
```

如果开启了 `AIWENDY_AUTO_INIT_TEST_USERS=1`，测试账号为：

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
   - 检查 `.env` 是否设置 `AIWENDY_AUTH_REQUIRED=0`
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
