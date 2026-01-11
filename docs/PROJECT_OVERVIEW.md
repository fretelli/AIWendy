# Project Overview

<a id="en"></a>
[English](#en) | [中文](#zh-cn)

This document is the “map” of the repository: where the code lives, which flows matter, and where to start reading.

## TL;DR

- Web: `aiwendy/apps/web` (Next.js)
- API: `aiwendy/apps/api` (FastAPI)
- DB: Postgres + `pgvector` (Docker Compose)
- Async jobs: Celery (optional profile in Compose)

## Repository layout

Top-level:

- `README.md` / `README.zh-CN.md`: first entry point
- `docs/`: repo-level documentation + design/history archives
- `aiwendy/`: the actual application (Compose + apps)

Application (`aiwendy/`):

- `aiwendy/apps/web`: Next.js UI
- `aiwendy/apps/api`: FastAPI backend
- `aiwendy/migrations`: Alembic migrations
- `aiwendy/docker-compose.yml`: local stack (db/redis/api/web + optional workers)

## Core flows (end-to-end)

### 1) Auth (guest-first self-hosting)

Goal: self-host users can run the app without creating accounts; production can enforce login.

- API: `aiwendy/apps/api/core/auth.py`
  - When `AIWENDY_AUTH_REQUIRED=0` and request has no token, API returns a local guest user (`guest@local.aiwendy`).
- Web: `aiwendy/apps/web/lib/auth-context.tsx`
  - Calls `/api/proxy/v1/users/me` and trusts API behavior (guest vs 401) instead of relying on a front-end flag.
- Login UI: `aiwendy/apps/web/app/auth/login/page.tsx`
  - Detects guest availability and shows “Continue as Guest”.

### 2) Chat (single coach)

- UI: `aiwendy/apps/web/app/(dashboard)/chat/page.tsx`
- API router: `aiwendy/apps/api/routers/chat.py`
- Streaming transport: SSE

### 3) Roundtable (multi-coach discussion)

Highlights:

- Session-level settings (persisted): model + KB (RAG) settings
- Message-level overrides: override provider/model/temperature/max_tokens and KB settings “for this message only”
- Attachments metadata: stored as JSON (no raw base64 persisted)

Relevant code:

- UI: `aiwendy/apps/web/app/(dashboard)/roundtable/page.tsx`
- UI streaming + composer: `aiwendy/apps/web/components/roundtable/RoundtableChat.tsx`
- API router: `aiwendy/apps/api/routers/roundtable.py`
- DB migration: `aiwendy/migrations/versions/009_add_roundtable_settings_and_attachments.py`

### 4) Knowledge Base (RAG)

- UI: `aiwendy/apps/web/app/(dashboard)/knowledge/page.tsx`
- API router: `aiwendy/apps/api/routers/knowledge.py`
- Storage: Postgres + pgvector

### 5) Files / attachments

Typical pipeline:

- Upload file
- Extract text (documents) / transcribe (audio) / embed base64 for images only when sending to model

API endpoints live under `aiwendy/apps/api/routers/files.py` (and are consumed by the shared web input components).

## Running locally

Recommended:

- `cd aiwendy`
- `Copy-Item .env.example .env` (PowerShell)
- `docker compose up -d --build`

See `aiwendy/docs/SELF_HOSTING.md` for guest mode and troubleshooting.

## Where to start as a contributor

Pick one entry:

- UI behavior: start from `aiwendy/apps/web/app/(dashboard)/...` routes
- API endpoints: start from `aiwendy/apps/api/routers/...`
- Data model: start from `aiwendy/apps/api/domain/...` and `aiwendy/migrations/...`

Then follow the data flow:

1. UI calls `aiwendy/apps/web/lib/api/*`
2. API router validates + loads user (`core/auth.py`)
3. Domain services and DB models execute
4. Streaming responses are sent via SSE back to the UI

---

<a id="zh-cn"></a>
## 中文

本文是仓库的“地图”：代码放在哪里、哪些链路最重要，以及从哪里开始读代码。

### TL;DR

- Web：`aiwendy/apps/web`（Next.js）
- API：`aiwendy/apps/api`（FastAPI）
- DB：Postgres + `pgvector`（Docker Compose）
- 异步任务：Celery（Compose 里可选 profile）

### 仓库结构

顶层：

- `README.md` / `README.zh-CN.md`：仓库入口
- `docs/`：仓库级文档 + 设计/历史归档
- `aiwendy/`：实际应用（Compose + apps）

应用目录（`aiwendy/`）：

- `aiwendy/apps/web`：Next.js 前端
- `aiwendy/apps/api`：FastAPI 后端
- `aiwendy/migrations`：Alembic 迁移
- `aiwendy/docker-compose.yml`：本地一键栈（db/redis/api/web + 可选 worker/beat）

### 核心链路（端到端）

#### 1) 认证（自托管优先访客模式）

目标：自托管用户开箱即用，无需创建账号；生产环境可强制登录。

- API：`aiwendy/apps/api/core/auth.py`
  - 当 `AIWENDY_AUTH_REQUIRED=0` 且请求没有 token 时，API 返回本地 guest 用户（`guest@local.aiwendy`）。
- Web：`aiwendy/apps/web/lib/auth-context.tsx`
  - 调用 `/api/proxy/v1/users/me`，信任后端返回（guest vs 401），而不是依赖前端开关。
- 登录页：`aiwendy/apps/web/app/auth/login/page.tsx`
  - 会检测后端是否支持 guest 并展示 “Continue as Guest”。

#### 2) 对话（单教练）

- UI：`aiwendy/apps/web/app/(dashboard)/chat/page.tsx`
- API 路由：`aiwendy/apps/api/routers/chat.py`
- 流式传输：SSE

#### 3) 圆桌讨论（多教练协作）

特点：

- 会话级设置（持久化）：模型 + 知识库（RAG）设置
- 消息级覆盖：针对“这条消息”覆盖 provider/model/temperature/max_tokens，以及知识库设置
- 附件元数据：JSON 存储（不持久化 raw base64）

相关代码：

- UI：`aiwendy/apps/web/app/(dashboard)/roundtable/page.tsx`
- UI 流式 + 输入框：`aiwendy/apps/web/components/roundtable/RoundtableChat.tsx`
- API 路由：`aiwendy/apps/api/routers/roundtable.py`
- DB 迁移：`aiwendy/migrations/versions/009_add_roundtable_settings_and_attachments.py`

#### 4) 知识库（RAG）

- UI：`aiwendy/apps/web/app/(dashboard)/knowledge/page.tsx`
- API 路由：`aiwendy/apps/api/routers/knowledge.py`
- 存储：Postgres + pgvector

#### 5) 文件 / 附件

典型处理流程：

- 上传文件
- 文档提取文本 / 音频转写 / 图片只在发送到模型时按需 base64

API 端点在 `aiwendy/apps/api/routers/files.py`（并由前端共享的输入组件消费）。

### 本地运行

推荐：

- `cd aiwendy`
- `Copy-Item .env.example .env`（PowerShell）
- `docker compose up -d --build`

访客模式与排错见：`aiwendy/docs/SELF_HOSTING.md`。

### 作为贡献者从哪里开始

选一个入口：

- UI 行为：从 `aiwendy/apps/web/app/(dashboard)/...` 路由开始
- API 端点：从 `aiwendy/apps/api/routers/...` 开始
- 数据模型：从 `aiwendy/apps/api/domain/...` 和 `aiwendy/migrations/...` 开始

然后沿着数据流往下走：

1. UI 调用 `aiwendy/apps/web/lib/api/*`
2. API router 校验并加载 user（`core/auth.py`）
3. Domain services 与 DB models 执行业务
4. 流式响应通过 SSE 回传给 UI
