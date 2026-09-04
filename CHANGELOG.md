# Changelog

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

本文件只记录可由当前仓库和 Git tag 验证的重要变更。

## 未发布

## 0.8.9 - 2026-09-04

- 期权结构化数据能力改为运营方容量停用：保留历史物理表，但市场 API 不再查询期权表，并以 HTTP 200 返回明确的 unavailable 状态。
- 04 宏观“历史位置”支持5年、10年、20年和截至当时全部历史四种点时比较基准，并与图表展示范围明确分离；修复滚动窗口边界多计一期，同时隐藏主值已为同比时重复且不适用的同比分析入口。
- 04 宏观六类完整结构化卡片直接展示关键细分结构；GDP 可见第一、第二、第三产业同比并可直接进入对应官方字段历史。下钻改为单图聚焦分析，PPI/PMI 大目录支持分组搜索，利率卡片进入完整利率工作台。
- 04 市场模块新增可交互利率与收益率工作台，接入 SHIBOR、LPR、USD LIBOR/HIBOR 历史、美国短期国债、长期国债和实际长期平均利率，并明确标注 LIBOR/HIBOR 的历史截止日期。
- 中国宏观指标接入经济发布日程，展示下一次计划发布时间、等待源端实际值状态以及最新正式值。
- 升级 ECharts、Nano ID、PyPDF 与 Pydantic AI 依赖，修复发布审计发现的 XSS、拒绝服务和 PDF 解析漏洞。
- 估值分位矩阵和排序表支持鼠标、全屏与键盘下钻，提供 1M–5Y PE/PB、历史分位、拥挤覆盖、前十大成分与方法说明；新增真实“我的持仓行业”筛选，历史不足时明确显示补录范围且不插值。
- 修复紧凑 Agent 对话发送失败时无提示且清空输入的问题；失败内容会保留，网络、限流和服务端错误可直接重试。
- AgentOS 市场历史范围增加真实 5Y，明确禁用无正式来源的 10Y；历史接口按日期去重并返回顺序快照。
- 放大估值表与相关矩阵的嵌入字号，并增加全屏 `+ / − / 0` 字号控制。
- 增加 `uploaded_files` Alembic 迁移，恢复附件元数据持久化。

## 0.3.0 - 2026-07-25

### 破坏性变更

- 删除旧项目、交易日志、交易所、行情代理、任务监控、教练与用户 API Key 接口；模型 BYOK 统一使用 `/api/v1/agent/model-credentials`。
- 运行时数据库管理统一为 Alembic，删除 `create_all`、临时建表脚本和测试用户自动初始化。
- 用户资料 API 只保留认证与基础资料字段；旧数据库列和历史迁移继续保留以支持已有部署升级。

### 变更

- 将公开定位统一为垂直投资 Research OS 与单一 Research Agent，不宣称通用电脑 Agent 或多智能体平台。
- 删除 Web 中无入口的旧交易、项目、教练、订阅与图表代码及其依赖。
- 增加签名提交、签名 tag、稳定安全门禁和按路径执行的自托管冷启动门禁。

## 0.2.1 - 2026-07-25

### 修复

- 股东扫描 watermark 改用已索引的公告日与报告期，避免大表全量扫描超时。
- 期权机会刷新只读取最近仍活跃系列的两个最新交易日，并复用现有系列日期复合索引。

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

## 0.8.9 - 2026-09-04

- Mark structured option data as operator-disabled for capacity reasons: retain historical physical tables, stop querying them from market APIs, and return an explicit unavailable state with HTTP 200.
- Let module-04 macro historical position switch among point-in-time 5Y, 10Y, 20Y, and expanding-history benchmarks independently of the chart display range. Fix the rolling-window boundary overcount and hide the duplicate inapplicable YoY analysis when the headline is already an official YoY series.
- Surface key provider-native structures directly on all six complete module-04 macro cards. GDP shows primary, secondary, and tertiary industry YoY with exact-field history links; drilldown now uses one focused chart, large PPI/PMI catalogs are searchable by group, and rate cards open the complete rates workspace.
- Add an interactive rates and yields workspace to Market module 04 with SHIBOR, LPR, historical USD LIBOR/HIBOR, US Treasury bills, long-term Treasury rates, and the real long-term average rate, including explicit historical cutoffs for LIBOR/HIBOR.
- Integrate the China economic release calendar into macro indicators with the next scheduled release, awaiting-source-value state, and latest formal value.
- Upgrade ECharts, Nano ID, PyPDF, and Pydantic AI dependencies to resolve release-audit XSS, denial-of-service, and PDF parsing advisories.
- Add mouse, fullscreen and keyboard valuation drilldowns with 1M–5Y PE/PB, percentiles, crowding coverage, top constituents and methodology; make Held Industries use real non-zero active-account A-share positions and disclose partial backfill without interpolation.
- Preserve Agent prompt text and show retryable errors when compact-dock message submission fails.
- Add a genuine 5Y AgentOS market history range, explicitly disable unsupported 10Y history, and deduplicate snapshots by date.
- Increase valuation-table and correlation-matrix readability with fullscreen `+ / − / 0` font controls.
- Add the missing `uploaded_files` Alembic migration for attachment metadata.

## 0.3.0 - 2026-07-25

### Breaking

- Removed legacy project, trading-journal, exchange, market-data proxy, task-monitoring, coach, and user API-key endpoints. Model BYOK now uses `/api/v1/agent/model-credentials` exclusively.
- Made Alembic the only runtime schema-management path and removed `create_all`, ad-hoc schema scripts, and automatic test-user initialization.
- Reduced user profile APIs to authentication and basic profile fields. Historical columns and migrations remain for upgrades of existing installations.

### Changed

- Standardized public positioning on a vertical investment Research OS with one focused Research Agent, without general computer-agent or multi-agent platform claims.
- Removed unreachable Web trading, project, coach, subscription, and chart code with unused dependencies.
- Added signed-commit/tag governance, a stable security gate, and a path-aware self-host clean-room gate.

## 0.2.1 - 2026-07-25

### Fixed

- Use indexed announcement and reporting dates for the holder scan watermark instead of a full-table update timestamp aggregate.
- Limit option opportunity refreshes to the two latest dates of recently active series and reuse the existing series-date indexes.

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
