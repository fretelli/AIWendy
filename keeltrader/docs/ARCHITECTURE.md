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

- AgentOS：每日基本面投研简报、深度研究 memo、决策日志、周度复盘、经验 lessons、基本面假设与验证记录
- Report KB：通过 report-kb 接入研报语义搜索，返回结构化研报命中结果供 AgentOS 使用
- Tushare Read：读取外部 Tushare 数据库表，应用内不要求配置 Tushare token
- Chat：SSE 流式对话，会话/消息持久化
- Settings/Auth：用户认证、登录保护、模型和连接配置

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

### 研报知识库检索

1. Web/API 提交查询、公司筛选和 top_k
2. API 通过 report-kb 服务执行语义检索
3. 结构化命中返回给 AgentOS，用于投研 memo、简报或人工判断

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

- AgentOS: daily fundamental briefs, deep research memos, decision journals, weekly reviews, lessons, fundamental hypotheses, and thesis validation records
- Report KB: integrates with report-kb for semantic research-report search and structured hits
- Tushare Read: reads from an external Tushare database; no in-app Tushare token is required
- Chat: SSE streaming chat, persisted sessions/messages
- Settings/Auth: user authentication, login protection, model settings, and connection configuration

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

#### Report knowledge-base search

1. Web/API submits query, company filters, and top_k
2. API calls report-kb for semantic search
3. Structured hits are returned to AgentOS for research memos, briefs, or human review
# Research event loop

KeelTrader 将机会、公司档案、股东披露和人工论点统一为用户隔离的研究事件闭环：后台任务只在不可变源快照发生真实变化时写入事件；首版档案、首次股东扫描和既有机会基线不生成未读洪水。全局机会只向明确关注且未暂停的用户发出站内事件。

`research_theses` 保存当前人工确认状态，`research_thesis_versions` 永久保存每次字段级变化，`research_thesis_evidence_links` 关联不可变证据。研报证据必须同时具备正文摘录与页码或章节定位；仅标题命中只用于导航。市场数据只有在用户显式创建上下文快照后才能进入 AI。

`GET /api/v1/markets/data-status` 只读展示宏观、利率和机会后台任务的源覆盖、起止日期、点数、最近成功、错误和耗时，不触发请求时刷新。中国现券国债曲线在授权来源缺失时明确不可用，不以期货或其他价格合成替代。
