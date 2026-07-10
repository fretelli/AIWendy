# Contributing / 贡献指南

KeelTrader 的默认开发分支是 `v2`。提交应聚焦基本面投资研究 AgentOS，不重新引入自动交易、技术分析、交易心理教练、交易所连接或商业化商城界面。

## Workflow

1. 从最新 `v2` 创建功能分支。
2. 保持改动聚焦，并为行为变化补充测试。
3. 提交 Pull Request 到 `v2`。
4. 使用 Conventional Commits，例如 `feat: ...`、`fix: ...`、`refactor: ...`。

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

The default development branch is `v2`. Changes should support the fundamental investment research AgentOS and must not reintroduce automated trading, technical analysis, trading-psychology coaching, exchange connections, or commerce surfaces.

Create a focused branch from `v2`, add tests for behavioral changes, use Conventional Commits, and target pull requests to `v2`. Run the checks above before opening a pull request. Report vulnerabilities through the process in [SECURITY.md](SECURITY.md), not through public issues.
