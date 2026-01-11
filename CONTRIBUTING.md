# Contributing

<a id="en"></a>
[English](#en) | [中文](#zh-cn)

Thanks for your interest in contributing to AIWendy!

## Quick start (recommended)

The easiest way to run the full stack locally is Docker Compose:

1. `cd aiwendy`
2. Copy env file: `Copy-Item .env.example .env` (PowerShell) or `cp .env.example .env`
3. Start: `docker compose up -d --build`

More details: `aiwendy/docs/SELF_HOSTING.md`

## Development (split mode)

You can also run DB/Redis in Docker and run the API/Web on your host:

- API: `aiwendy/docs/DEPLOYMENT.md`
- Web: `aiwendy/apps/web/package.json` scripts: `npm run dev`, `npm run lint`, `npm run type-check`

## Pull requests

- Keep PRs focused (one topic per PR).
- Include screenshots/GIFs for UI changes.
- Prefer adding/adjusting docs if behavior changes.
- Ensure CI passes (lint/type-check/compile checks).

## Reporting bugs / requesting features

Please use GitHub Issues and include:

- What you expected vs what happened
- Steps to reproduce
- Logs (redact secrets)
- OS / Node / Python versions

## Security

If you believe you found a security issue, please follow `SECURITY.md` instead of opening a public issue.

---

<a id="zh-cn"></a>
## 中文

感谢你愿意为 AIWendy 做贡献！

### 快速开始（推荐）

最简单的本地运行方式是使用 Docker Compose：

1. `cd aiwendy`
2. 复制环境变量文件：PowerShell 用 `Copy-Item .env.example .env`，macOS/Linux 用 `cp .env.example .env`
3. 启动：`docker compose up -d --build`

更多细节：`aiwendy/docs/SELF_HOSTING.md`

### 开发（拆分模式）

你也可以只用 Docker 跑 DB/Redis，然后在宿主机运行 API/Web：

- API：`aiwendy/docs/DEPLOYMENT.md`
- Web：参考 `aiwendy/apps/web/package.json` scripts：`npm run dev`、`npm run lint`、`npm run type-check`

### Pull Request

- 保持 PR 聚焦（一个 PR 一个主题）。
- UI 变更请补充截图/GIF。
- 如果行为有变化，优先补充/调整文档。
- 确保 CI 通过（lint/type-check/compile checks）。

### 报告 Bug / 提需求

请使用 GitHub Issues，并包含：

- 期望行为 vs 实际发生了什么
- 复现步骤
- 日志（注意脱敏，不要提交密钥）
- OS / Node / Python 版本

### 安全

如果你认为发现了安全问题，请按 `SECURITY.md` 处理，不要直接开公开 Issue。
