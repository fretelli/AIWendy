# 系统架构（以代码为准）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

KeelTrader 采用前后端分离架构：Next.js 负责 Web UI，FastAPI 提供业务 API；PostgreSQL（pgvector）存储结构化数据与向量；Redis 用于缓存/限流与 Celery 队列。

## 组件关系

```
Browser
  │  HTTP(S)
  ▼
Next.js (apps/web) ───────────────┐
  │  API proxy / fetch            │
  ▼                               │
FastAPI (apps/api)                │
  │                               │
  ├─ PostgreSQL + pgvector (db)   │
  └─ Redis (redis) ── Celery worker/beat（可选）
```

## 代码结构（核心）

- `apps/web/`：Next.js 14 App Router 前端
- `apps/api/`：FastAPI 后端
- `migrations/`：Alembic 迁移
- `docker-compose.yml`：自托管编排

## 核心业务模块

- Projects：项目分组与数据隔离（前后端均支持按 `project_id` 过滤）
- Chat：SSE 流式对话，会话/消息持久化
- Knowledge Base：文档导入、向量化、检索；聊天可选择注入检索结果（RAG）
- Trading Log：交易日志 CRUD + 统计 + AI 分析
- Reports：日报/周报/月报生成、列表/详情、定时设置（可走异步任务）

## 数据与异步任务

- PostgreSQL：主数据存储；知识库向量使用 pgvector 列 + 向量索引
- Redis：
  - 限流/短期缓存（例如分析、检索结果）
  - Celery broker/result backend（当启用 worker/beat 时）
- Celery worker/beat：用于报告生成、知识库导入等耗时任务（可选）

## 关键请求链路（示例）

### 聊天（SSE）

1. Web 发起请求（带上会话/模型/配置参数）
2. API 生成/续写消息并以 SSE 分块返回
3. 同步写入会话与消息记录，便于历史回溯

### 知识库检索（RAG）

1. 文档导入：分段 → 生成向量 → 写入 pgvector
2. 对话时：对用户输入向量化 → 相似检索 → 将命中文本拼入 prompt → 生成回答

---

<a id="en"></a>
## English

KeelTrader uses a decoupled web/API architecture: Next.js provides the Web UI, FastAPI provides business APIs; PostgreSQL (pgvector) stores structured data and embeddings; Redis is used for caching/rate limiting and Celery queues.

### Component relationships

```
Browser
  │  HTTP(S)
  ▼
Next.js (apps/web) ───────────────┐
  │  API proxy / fetch            │
  ▼                               │
FastAPI (apps/api)                │
  │                               │
  ├─ PostgreSQL + pgvector (db)   │
  └─ Redis (redis) ── Celery worker/beat (optional)
```

### Code structure (core)

- `apps/web/`: Next.js 14 App Router frontend
- `apps/api/`: FastAPI backend
- `migrations/`: Alembic migrations
- `docker-compose.yml`: self-hosting orchestration

### Core business modules

- Projects: project grouping and data isolation (`project_id` filtering supported end-to-end)
- Chat: SSE streaming chat, persisted sessions/messages
- Knowledge Base: document import, embedding, retrieval; chat can inject retrieval results into prompts (RAG)
- Trading Log: CRUD + stats + AI analysis
- Reports: daily/weekly/monthly generation, list/detail, scheduling (can run via async tasks)

### Data & async jobs

- PostgreSQL: primary datastore; KB vectors use pgvector columns + vector indexes
- Redis:
  - Rate limiting / short-lived cache (e.g. analysis/retrieval results)
  - Celery broker/result backend (when worker/beat is enabled)
- Celery worker/beat: report generation, KB import, and other long-running tasks (optional)

### Key request flows (examples)

#### Chat (SSE)

1. Web sends a request (session/model/config params)
2. API generates/continues content and streams chunks via SSE
3. Sessions and messages are stored for history

#### Knowledge retrieval (RAG)

1. Import: chunk → embed → write to pgvector
2. During chat: embed user input → similarity search → inject matched text into prompt → generate response

