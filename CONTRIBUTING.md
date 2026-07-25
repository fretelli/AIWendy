# Contributing / 贡献指南

KeelTrader 的默认开发分支是 `v2`。提交应聚焦垂直投资 Research OS，不重新引入自动交易、技术分析、交易心理教练、交易所连接、通用电脑 Agent 或商业化商城界面。`v2` 禁止直接推送，所有改动必须通过 Pull Request 和完整 CI。

## Workflow

1. 从最新 `v2` 创建功能分支。
2. 保持改动聚焦，并为行为变化补充测试。
3. 提交 Pull Request 到 `v2`。
4. 使用 Conventional Commits，例如 `feat: ...`、`fix: ...`、`refactor: ...`。

新增、删除或改名 Markdown 文档时，必须同步更新 `.github/public-docs-allowlist.txt`。私有运维笔记、凭证、事故记录和会议纪要不得进入公开仓库。

维护者生产环境的域名、反向代理、宿主机路径、定时任务和发布凭据必须保存在私有基础设施仓库。Public 仓库只接受可移植的自托管定义。GitHub Actions 必须固定到完整提交 SHA，并保留版本注释供 Dependabot 更新。

## Local Checks

```bash
cd keeltrader
make check-security-defaults
make audit-root
make check-web
make audit-web
make check-api-static
make check-api
make audit-api
```

Web 与 API 的详细环境说明见：

- [Self-hosting](keeltrader/docs/SELF_HOSTING.md)
- [Architecture](keeltrader/docs/ARCHITECTURE.md)
- [Deployment](keeltrader/docs/DEPLOYMENT.md)

安全问题不要提交公开 Issue，请遵循 [SECURITY.md](SECURITY.md)。

---

The default development branch is `v2`. Direct pushes are blocked; every change must go through a pull request and the complete CI suite. Changes should support the vertical investment Research OS and must not reintroduce automated trading, technical analysis, trading-psychology coaching, exchange connections, general computer agents, or commerce surfaces.

Create a focused branch from `v2`, add tests for behavioral changes, use Conventional Commits, and target pull requests to `v2`. Run the checks above before opening a pull request. Report vulnerabilities through the process in [SECURITY.md](SECURITY.md), not through public issues.

When adding, deleting, or renaming Markdown documentation, update `.github/public-docs-allowlist.txt` in the same pull request. Private operations notes, credentials, incident records, and meeting notes do not belong in the public repository.

Maintainer domains, reverse proxies, host paths, schedules, and release credentials belong in a private infrastructure repository. The public repository accepts only portable self-host definitions. GitHub Actions must be pinned to full commit SHAs with version comments retained for Dependabot.
