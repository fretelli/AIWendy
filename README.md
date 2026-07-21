# KeelTrader

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

KeelTrader 是一个面向个人或小团队的投资研究操作系统。产品中只有一个 KeelTrader 研究助手，统一承载会话、股东追踪、市场原始数据、研报证据与基本面假设验证。

它的定位是研究辅助与纪律引擎，而不是自动赚钱机器。系统默认要求登录，强调 human-in-the-loop：AI 可以帮助检索、分析、辩论、记录和复盘，但最终交易决策应由人完成。

## 核心能力

- 统一研究工作台：持久化会话、BYOK、用户 MCP、工具审批、预算、可回滚记忆与定时研究。
- 市场工作区：A 股资金、宏观、期货和期权的全量原始历史；原生图表提示跟随并约束在鼠标附近，来源新鲜度区分交易日与自然日滞后；期货/期权与底层标的分开展示，不使用均线、百分位、IV、Greeks 或合成补齐。
- 显式证据带入：市场数据默认不进入 AI 上下文；只在用户点击“带入研究”后创建不可变快照。
- 研报知识库：接入 report-kb，支持研报语义搜索和结构化命中结果。
- 结构化数据读取：接入 Tushare 数据库读服务，不要求在应用内配置 Tushare token。
- 研究模式：同一助手支持直接问答、深度研究、计划、反证与复盘。
- 安全边界：公网部署默认登录保护，不自动下单，不把 AI 输出当作投资建议。

KeelTrader 当前不提供技术分析、自动交易、交易所连接、交易心理教练、积分商城或会员 SaaS。历史数据库迁移仍保留，以兼容已有部署。

## 仓库结构

- `keeltrader/`：应用源码、Docker Compose、迁移、测试和运行文档。
- `.github/`：CI、发布工作流和 Issue 模板。
- 根目录：项目介绍、许可证、安全政策和贡献指南。

## 架构

- `keeltrader/apps/web/`：Next.js App Router 前端。
- `keeltrader/apps/api/`：FastAPI 后端，提供认证、Agent Platform、研报搜索、设置等 API。
- `agent-platform-worker`：复用 API 镜像运行可恢复 Agent 任务 Worker 和定时研究调度。
- PostgreSQL / pgvector：结构化数据、日志、记忆与向量检索存储。
- Redis：缓存、限流、任务队列和 Agent Platform 心跳。

## 快速开始

自托管部署使用隔离编排 `docker-compose.selfhost.yml`，自带 PostgreSQL/pgvector 与 Redis。默认仅使用管理员配置的只读 report-kb；可选 Research Cloud 连接器必须由管理员显式启用，并由每位用户独立授权，且不会上传本地文档、持仓、交易、模型密钥或决策日志。

自托管 Agent 平台不内置平台所有者的模型 Token。每位用户通过 `/agent` 保存自己的 BYOK；密钥加密存储且不进入日志、任务事件、记忆或 MCP 参数。用户 MCP 默认只允许公网 HTTPS，首次按工具授权，定时任务只能使用永久授权工具。Agent 平台仅提供研究与决策日志能力，不注册下单、撤单、Ghost Trade 或任意代码执行工具。

```bash
cd keeltrader
cp .env.example .env
docker compose -f docker-compose.selfhost.yml up -d --build
docker compose -f docker-compose.selfhost.yml exec -T api alembic upgrade head
```

更多说明：

- [自托管](keeltrader/docs/SELF_HOSTING.md)
- [系统架构](keeltrader/docs/ARCHITECTURE.md)
- [部署与发布](keeltrader/docs/DEPLOYMENT.md)
- [自定义 LLM / OpenAI 兼容 API](keeltrader/docs/CUSTOM_API_SETUP.md)

## GitHub 展示同步

`README.md` 会随默认分支 push 自动更新。GitHub 右侧 About 栏是仓库元数据，不会自动读取 README；如需同步 description/topics，请在已登录 GitHub CLI 的环境运行：

```bash
keeltrader/scripts/sync-github-about.sh
```

## 风险提示

KeelTrader 不构成投资建议，也不保证跑赢市场。LLM 可能产生幻觉、遗漏上下文或误读数据；假设验证也可能存在过拟合、幸存者偏差和数据泄漏。请把它作为投研效率、决策一致性和复盘纪律工具，而不是自动交易或收益承诺系统。

---

<a id="en"></a>
## English

KeelTrader is a self-evolving fundamental investment research Agent Platform for individual investors and small teams. It provides multi-agent research assistance, report-KB search, structured decision journals, weekly reviews, and fundamental thesis validation records.

Its role is a research assistant and discipline engine, not an automatic money-making system. Production deployments require authentication by default and keep humans in the loop: AI can retrieve, analyze, debate, record, and review, while final trading decisions remain human decisions.

## Core Capabilities

- Unified Agent workspace: durable research runs, declarative custom agents, BYOK, user MCP, approvals, budgets, reversible memory, and scheduled research.
- Report knowledge base: integrates with report-kb for semantic research-report search and structured hits.
- Structured data reads: reads from a Tushare database service without requiring an in-app Tushare token.
- Multi-agent analysis: supports composable fundamental, macro, sentiment, red-team, and review workflows.
- Safety boundary: login-protected by default, no automatic order execution, and AI output is not investment advice.

KeelTrader currently does not provide technical analysis, automated trading, exchange connections, trading-psychology coaching, a points mall, or membership SaaS. Historical database migrations remain for compatibility with existing deployments.

## Repository Layout

- `keeltrader/`: application source, Docker Compose, migrations, tests, and operational documentation.
- `.github/`: CI, release workflows, and issue templates.
- Repository root: product overview, license, security policy, and contribution guide.

## Architecture

- `keeltrader/apps/web/`: Next.js App Router frontend.
- `keeltrader/apps/api/`: FastAPI backend for auth, Agent Platform, report search, settings, and related APIs.
- `agent-platform-worker`: reuses the API image for resumable Agent work and scheduled research.
- PostgreSQL / pgvector: structured records, journals, memory, and vector search storage.
- Redis: cache, rate limiting, task queues, and Agent Platform heartbeat.

## Quick Start

Self-hosting uses the isolated `docker-compose.selfhost.yml` stack with PostgreSQL/pgvector and Redis included. It uses an administrator-configured read-only report-kb by default. The optional Research Cloud connector must be explicitly enabled by an administrator and authorized separately by each user; it never uploads local documents, positions, trades, model credentials, or decision journals.

The self-hosted Agent Platform never bundles an operator model token. Users add encrypted BYOK profiles in `/agent`. Secrets are excluded from logs, task events, memory, and MCP parameters. User MCP is public-HTTPS-only by default and requires per-tool approval; scheduled runs can use only permanently approved tools. The platform exposes research and decision-journal capabilities only—no order placement, cancellation, ghost trading, or arbitrary code execution.

```bash
cd keeltrader
cp .env.example .env
docker compose -f docker-compose.selfhost.yml up -d --build
docker compose -f docker-compose.selfhost.yml exec -T api alembic upgrade head
```

Further reading:

- [Self-hosting](keeltrader/docs/SELF_HOSTING.md)
- [Architecture](keeltrader/docs/ARCHITECTURE.md)
- [Deployment](keeltrader/docs/DEPLOYMENT.md)
- [Custom LLM / OpenAI-compatible APIs](keeltrader/docs/CUSTOM_API_SETUP.md)

## GitHub Display Sync

`README.md` updates automatically when the default branch is pushed. The GitHub About sidebar is repository metadata and does not read from the README automatically. To sync description/topics, run this from an authenticated GitHub CLI environment:

```bash
keeltrader/scripts/sync-github-about.sh
```

## Disclaimer

KeelTrader is not investment advice and does not guarantee outperformance. LLMs can hallucinate, miss context, or misread data; hypothesis validation can still suffer from overfitting, survivorship bias, and data leakage. Treat it as a tool for research efficiency, decision consistency, and review discipline, not as an automated trading or return-guarantee system.
