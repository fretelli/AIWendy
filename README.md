# AIWendy

[English](README.md) | [简体中文](README.zh-CN.md)

<a id="en"></a>
[English](#en) | [简体中文](#zh-cn)

[![CI](https://github.com/fretelli/AIWendy/actions/workflows/ci.yml/badge.svg)](https://github.com/fretelli/AIWendy/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

AIWendy is an AI-powered performance coach for trading psychology (Web: Next.js, API: FastAPI). It’s built around chat, knowledge base (RAG), and a “roundtable” multi-coach discussion mode.

Disclaimer: for educational/research purposes only. This project is **not** investment advice.

## Screenshots

![Overview](docs/assets/overview.svg)

![Roundtable](docs/assets/roundtable.svg)

![Architecture](docs/assets/architecture.svg)

## What you can do

- **Chat + projects**: organize conversations per project, keep history, stream responses (SSE)
- **Roundtable discussion**: multiple AI coaches discuss one question with configurable session/message settings
- **Knowledge base (RAG)**: import docs, semantic search (pgvector), inject context by timing
- **Attachments**: upload images/docs/audio (extract/transcribe where supported)
- **Journaling + reports**: trading journal, analytics, scheduled reports (Celery)
- **Journal import (CSV/XLSX)**: upload a file and map columns in the UI (works with different broker/export formats)
- **Self-hosted by default**: Docker Compose; optional cloud/SaaS mode via env flags

## Quick start (self-host)

```bash
cd aiwendy
Copy-Item .env.example .env   # PowerShell (or: cp .env.example .env)
docker compose up -d --build
```

- Web: `http://localhost:3000`
- API health: `http://localhost:8000/api/health`
- API docs: `http://localhost:8000/docs`

Full guide: `aiwendy/docs/SELF_HOSTING.md`

## Guest mode (no login)

Set `AIWENDY_AUTH_REQUIRED=0` for the API (enabled by default in `aiwendy/docker-compose.yml`) to use the app without logging in.

## Roadmap (community)

- Add more “1-click demo” options (cloud deploy templates)
- Improve preset library and import/export
- More evaluators/benchmarks for coaching quality

## Docs

- Start here: `docs/README.md`
- Repo map: `docs/PROJECT_OVERVIEW.md`
- App docs: `aiwendy/docs/README.md`
- Architecture: `aiwendy/docs/ARCHITECTURE.md`
- Deployment: `aiwendy/docs/DEPLOYMENT.md`

## Contributing & security

- Contributing: `CONTRIBUTING.md`
- Code of Conduct: `CODE_OF_CONDUCT.md`
- Security policy: `SECURITY.md`

## Deployment modes (open core)

AIWendy supports two modes:

- **Self-hosted (default)**: open-source community edition
- **Cloud/SaaS**: multi-tenancy, billing, enterprise SSO, analytics (activated only when `DEPLOYMENT_MODE=cloud`)

See `docs/DEPLOYMENT_MODES.md` for details.

---

<a id="zh-cn"></a>
## 简体中文

AIWendy 是一套面向交易心理与行为表现的 AI 教练系统（Web: Next.js，API: FastAPI）。核心能力围绕：对话、知识库（RAG）、以及“圆桌讨论”（多教练协作）。

免责声明：仅用于教育/研究目的，本项目 **不构成** 投资建议。

### 截图 / 演示

![概览](docs/assets/overview.svg)

![圆桌讨论](docs/assets/roundtable.svg)

![架构](docs/assets/architecture.svg)

### 你可以用它做什么

- **对话 + 项目**：按项目组织会话，历史记录，SSE 流式输出
- **圆桌讨论**：多位 AI 教练围绕同一问题讨论；支持会话级/消息级设置
- **知识库（RAG）**：文档导入、pgvector 语义检索，按时机注入上下文
- **附件**：图片/文档/音频上传（按能力抽取/转写）
- **交易日志 + 报告**：交易日志、统计、定时报表（Celery）
- **交易日志导入（CSV/XLSX）**：支持上传文件并在页面中手动映射列（适配不同券商/平台格式）
- **默认可自托管**：Docker Compose 一键启动；也支持通过环境变量启用云端模式

### 快速开始（自托管）

```bash
cd aiwendy
Copy-Item .env.example .env   # PowerShell（或：cp .env.example .env）
docker compose up -d --build
```

- Web：`http://localhost:3000`
- API 健康检查：`http://localhost:8000/api/health`
- API 文档：`http://localhost:8000/docs`

完整说明：`aiwendy/docs/SELF_HOSTING.md`

### 访客模式（免登录）

将 API 的 `AIWENDY_AUTH_REQUIRED=0`（默认在 `aiwendy/docker-compose.yml` 已启用该能力）即可免登录体验。

### Roadmap（社区版）

- 增加更多“一键 Demo”部署模板
- 预设教练库的导入/导出与共享
- 教练效果的评测与对比工具

### 文档

- 从这里开始：`docs/README.md`
- 仓库导览：`docs/PROJECT_OVERVIEW.md`
- 应用文档：`aiwendy/docs/README.md`
- 架构：`aiwendy/docs/ARCHITECTURE.md`
- 部署：`aiwendy/docs/DEPLOYMENT.md`

### 贡献与安全

- 贡献指南：`CONTRIBUTING.md`
- 行为准则：`CODE_OF_CONDUCT.md`
- 安全策略：`SECURITY.md`

### 部署模式（Open Core）

AIWendy 支持两种模式：

- **Self-Hosted（默认）**：开源社区版
- **Cloud/SaaS**：多租户、计费、企业 SSO、分析（仅在 `DEPLOYMENT_MODE=cloud` 时启用）

详见：`docs/DEPLOYMENT_MODES.md`
