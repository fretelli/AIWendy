# Changelog

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

本文件只记录可由当前仓库和 Git tag 验证的重要变更。

## 未发布

- 暂无。

## 0.2.0 - 2026-07-25

### 变更

- 将项目定位统一为纯基本面投资研究 AgentOS。
- 以 `v2` 作为唯一开发与发布分支。
- 补充研报知识库检索、决策日志、周度复盘和基本面投资假设验证记录。
- 清理旧的交易心理教练、交易所、商城和 Cloud/SaaS 公开文档。
- 将维护者生产 Compose、域名、宿主机挂载、发布脚本和私人内容任务迁出 Public 仓库。
- 增加可移植的完整自托管拓扑、机会 Worker、冷启动验收、兼容矩阵和产品导览。
- 修复空数据库历史迁移链，并将 Web 运行镜像改为最小化 Next.js standalone 输出。

### 安全

- 公网部署默认要求登录，保留 human-in-the-loop 最终决策边界。
- 公开仓库安全检查会拒绝运行时凭证、私钥和旧产品定位。
- GitHub Actions 固定到不可变提交，并增加 CodeQL、依赖审查、SBOM、provenance 和镜像签名。

## 0.1.0 - 2026-01-13

- 首个公开版本。

---

<a id="en"></a>
## English

This file records only notable changes that can be verified from the current repository and Git tags.

## Unreleased

- None.

## 0.2.0 - 2026-07-25

### Changed

- Repositioned the project as a fundamental investment research AgentOS.
- Made `v2` the only development and release branch.
- Added report-KB search, decision journals, weekly reviews, and fundamental thesis validation records.
- Removed public documentation for the former trading-psychology, exchange, commerce, and Cloud/SaaS positioning.
- Moved maintainer production Compose, domains, host mounts, release scripts, and private content jobs out of the public repository.
- Added a portable full self-host topology, opportunity worker, clean-room smoke, compatibility matrix, and product walkthrough.
- Repaired the historical clean-database migration chain and minimized the Web runtime with Next.js standalone output.

### Security

- Public deployments require authentication by default and retain a human-in-the-loop final decision boundary.
- Public repository checks reject runtime credentials, private keys, and obsolete product positioning.
- GitHub Actions are pinned to immutable commits, with CodeQL, dependency review, SBOM, provenance, and image signing.

## 0.1.0 - 2026-01-13

- Initial public release.
