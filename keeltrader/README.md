# KeelTrader

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

KeelTrader 是一个自进化投资研究 AgentOS。它面向个人或小团队的投研流程，提供多 Agent 研究辅助、研报知识库搜索、结构化决策日志、周度复盘和策略假设/回测记录。

它的定位是研究辅助与纪律引擎，而不是自动赚钱机器。系统默认要求登录，强调 human-in-the-loop：AI 可以帮助检索、分析、辩论、记录和复盘，但最终交易决策应由人完成。

## 核心能力

- AgentOS 工作台：每日投研简报、深度研究 memo、决策日志、复盘 lessons、策略假设和回测记录。
- 研报知识库：接入 report-kb，支持研报语义搜索和结构化命中结果。
- 结构化数据读取：接入 Tushare 数据库读服务，不要求在应用内配置 Tushare token。
- 多 Agent 分析：支持宏观/技术/量化/情绪等研究角色的组合式分析工作流。
- 安全边界：公网部署默认登录保护，不自动下单，不把 AI 输出当作投资建议。

## 架构

- `apps/web/`：Next.js App Router 前端。
- `apps/api/`：FastAPI 后端，提供认证、AgentOS、研报搜索、设置等 API。
- `agent-engine`：复用 API 镜像运行 AgentOS 心跳与后台任务。
- PostgreSQL / pgvector：结构化数据、日志、记忆与向量检索存储。
- Redis：缓存、限流、任务队列和 AgentOS 心跳。

## 快速开始

自托管部署使用 Docker Compose。当前 compose 编排 `api`、`web` 和 `agent-engine`，PostgreSQL 与 Redis 作为外部服务接入。

```bash
cp .env.example .env
docker compose up -d api web agent-engine
docker compose exec -T api alembic upgrade head
```

更多说明：

- [自托管](docs/SELF_HOSTING.md)
- [系统架构](docs/ARCHITECTURE.md)
- [部署与发布](docs/DEPLOYMENT.md)
- [自定义 LLM / OpenAI 兼容 API](docs/CUSTOM_API_SETUP.md)

## GitHub 展示同步

`README.md` 会随默认分支 push 自动更新。GitHub 右侧 About 栏是仓库元数据，不会自动读取 README；如需同步 description/topics，请在已登录 GitHub CLI 的环境运行：

```bash
scripts/sync-github-about.sh
```

## 风险提示

KeelTrader 不构成投资建议，也不保证跑赢市场。LLM 可能产生幻觉、遗漏上下文或误读数据；回测也可能存在过拟合、幸存者偏差和数据泄漏。请把它作为投研效率、决策一致性和复盘纪律工具，而不是自动交易或收益承诺系统。

---

<a id="en"></a>
## English

KeelTrader is a self-evolving investment research AgentOS for individual investors and small teams. It provides multi-agent research assistance, report-KB search, structured decision journals, weekly reviews, and strategy hypothesis/backtest records.

Its role is a research assistant and discipline engine, not an automatic money-making system. Production deployments require authentication by default and keep humans in the loop: AI can retrieve, analyze, debate, record, and review, while final trading decisions remain human decisions.

## Core Capabilities

- AgentOS workspace: daily research briefs, deep research memos, decision journals, review lessons, strategy hypotheses, and backtest records.
- Report knowledge base: integrates with report-kb for semantic research-report search and structured hits.
- Structured data reads: reads from a Tushare database service without requiring an in-app Tushare token.
- Multi-agent analysis: supports composable macro, technical, quantitative, sentiment, and research workflows.
- Safety boundary: login-protected by default, no automatic order execution, and AI output is not investment advice.

## Architecture

- `apps/web/`: Next.js App Router frontend.
- `apps/api/`: FastAPI backend for auth, AgentOS, report search, settings, and related APIs.
- `agent-engine`: reuses the API image for AgentOS heartbeat and background tasks.
- PostgreSQL / pgvector: structured records, journals, memory, and vector search storage.
- Redis: cache, rate limiting, task queues, and AgentOS heartbeat.

## Quick Start

Self-hosting uses Docker Compose. The current compose file orchestrates `api`, `web`, and `agent-engine`; PostgreSQL and Redis are external services.

```bash
cp .env.example .env
docker compose up -d api web agent-engine
docker compose exec -T api alembic upgrade head
```

Further reading:

- [Self-hosting](docs/SELF_HOSTING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Custom LLM / OpenAI-compatible APIs](docs/CUSTOM_API_SETUP.md)

## GitHub Display Sync

`README.md` updates automatically when the default branch is pushed. The GitHub About sidebar is repository metadata and does not read from the README automatically. To sync description/topics, run this from an authenticated GitHub CLI environment:

```bash
scripts/sync-github-about.sh
```

## Disclaimer

KeelTrader is not investment advice and does not guarantee outperformance. LLMs can hallucinate, miss context, or misread data; backtests can suffer from overfitting, survivorship bias, and data leakage. Treat it as a tool for research efficiency, decision consistency, and review discipline, not as an automated trading or return-guarantee system.
