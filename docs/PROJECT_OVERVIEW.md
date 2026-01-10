# Project Overview

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

