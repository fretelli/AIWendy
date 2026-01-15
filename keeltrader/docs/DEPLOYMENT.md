# 部署与运行（开发/生产）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

如果你只需要本地一键运行，请直接看：`SELF_HOSTING.md`。

## 本地开发（两种方式）

### 方式 A：全部用 Docker（最省心）

按 `SELF_HOSTING.md` 启动即可；适合 Windows/macOS/Linux 通用。

### 方式 B：数据库/Redis 用 Docker，Web/API 在宿主机跑（适合 Linux/macOS/WSL）

1. 启动基础服务：

```bash
docker compose up -d db redis
```

2. 启动后端（FastAPI）：

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

3. 启动前端（Next.js）：

```bash
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## 生产部署（建议组合）

- Web：Vercel（或 Netlify）
- API：Railway / Fly.io / AWS ECS
- Postgres（pgvector）：Supabase / Neon / RDS
- Redis：Upstash（或自建）

### 必要环境变量（Web）

- `NEXT_PUBLIC_API_URL`（例如 `https://api.example.com`）
- `NEXTAUTH_URL`（例如 `https://app.example.com`）
- `NEXTAUTH_SECRET`

### 必要环境变量（API）

- `DATABASE_URL`（建议 `postgresql+asyncpg://...`）
- `REDIS_URL`
- `JWT_SECRET`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`（至少一个）

### 数据库初始化与迁移

确保数据库启用 pgvector：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

运行迁移：

```bash
alembic upgrade head
```

### 健康检查

- `GET /api/health`
- `GET /api/health/ready`

## 相关文档

- 项目状态（以代码为准）：`../../docs/PROJECT_STATUS.md`
- 自定义 LLM 配置：`../../docs/CUSTOM_API_SETUP.md`

---

<a id="en"></a>
## English

If you only need a one-click local run, see: `SELF_HOSTING.md`.

### Local development (two options)

#### Option A: everything in Docker (easiest)

Just follow `SELF_HOSTING.md`; works well across Windows/macOS/Linux.

#### Option B: DB/Redis in Docker, Web/API on host (good for Linux/macOS/WSL)

1. Start base services:

```bash
docker compose up -d db redis
```

2. Start backend (FastAPI):

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

3. Start frontend (Next.js):

```bash
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Production deployment (suggested stack)

- Web: Vercel (or Netlify)
- API: Railway / Fly.io / AWS ECS
- Postgres (pgvector): Supabase / Neon / RDS
- Redis: Upstash (or self-hosted)

#### Required env vars (Web)

- `NEXT_PUBLIC_API_URL` (e.g. `https://api.example.com`)
- `NEXTAUTH_URL` (e.g. `https://app.example.com`)
- `NEXTAUTH_SECRET`

#### Required env vars (API)

- `DATABASE_URL` (recommended: `postgresql+asyncpg://...`)
- `REDIS_URL`
- `JWT_SECRET`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (at least one)

#### DB initialization & migrations

Make sure `pgvector` is enabled:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Run migrations:

```bash
alembic upgrade head
```

#### Health checks

- `GET /api/health`
- `GET /api/health/ready`

### Related docs

- Project status (source of truth is code): `../../docs/PROJECT_STATUS.md`
- Custom LLM configuration: `../../docs/CUSTOM_API_SETUP.md`

