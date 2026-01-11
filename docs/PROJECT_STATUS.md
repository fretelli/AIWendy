# AIWendy 项目状态（以代码为准）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

更新时间：2026-01-09

## 结论

Community 版可用（自托管/本地可跑通主链路）。

**新增：** 现已支持开源 + 托管 SaaS 双模式部署。

> 说明：通过 `DEPLOYMENT_MODE` 环境变量控制部署模式。默认为 `self-hosted`（开源社区版），可设置为 `cloud`（托管 SaaS 版）。

## 部署模式

### 自托管模式（默认）
- 完全开源，Apache 2.0 许可证
- 核心功能完整可用
- 无使用限制
- 社区支持

### 云托管模式
- 多租户架构
- 使用分析（PostHog/Mixpanel）
- 企业 SSO（SAML/OAuth）
- Stripe 计费集成
- 资源配额管理

详见：`DEPLOYMENT_MODES.md` 和 `SAAS_MIGRATION_SUMMARY.md`

## 可用主链路

登录 → 选择项目 → 对话 / 知识库 / 交易日志 / 报告（均支持 `project_id` 维度）→ 查看历史与统计

## 主要能力（已实现）

- 用户系统：注册/登录/JWT，会话跟踪（`user_sessions`）
- Projects：`/api/v1/projects` + 前端 `/projects`
- 对话：SSE 流式输出、会话历史（`chat_sessions`/`chat_messages`）
- 知识库：`/api/v1/knowledge` 文档导入、pgvector 语义检索（可选 RAG 注入）
- 交易日志：CRUD + 统计 + AI 分析（支持 `project_id` 过滤）
- 报告：`/api/v1/reports` + 前端 `/reports`（列表/详情/定时配置）
- 异步任务：Celery worker/beat + `/api/v1/tasks`（报告生成、知识库导入队列/状态）
- Redis：限流 + 短 TTL 缓存（分析/检索）
- 自托管：Docker Compose（db/redis/api/web/worker/beat）

## 相关文档

- 自托管：`../aiwendy/docs/SELF_HOSTING.md`
- 部署：`../aiwendy/docs/DEPLOYMENT.md`
- LLM 配置：`CUSTOM_API_SETUP.md`

---

<a id="en"></a>
## English

Updated: 2026-01-09

### Conclusion

The Community edition is usable (self-hosted / local runs cover the main end-to-end flows).

**New:** dual deployment modes are now supported: open-source + hosted SaaS.

> Note: deployment mode is controlled via the `DEPLOYMENT_MODE` env var. Default is `self-hosted` (open-source community edition). Set it to `cloud` to enable hosted SaaS mode.

### Deployment modes

#### Self-hosted (default)

- Fully open-source (Apache 2.0)
- Core features available
- No usage limits
- Community support

#### Cloud-hosted

- Multi-tenant architecture
- Analytics (PostHog/Mixpanel)
- Enterprise SSO (SAML/OAuth)
- Stripe billing integration
- Resource quota management

See: `DEPLOYMENT_MODES.md` and `SAAS_MIGRATION_SUMMARY.md`

### Main user flows available

Login → pick a project → chat / knowledge base / trading log / reports (all support `project_id` scoping) → view history and stats

### Major capabilities implemented

- User system: signup/login/JWT, session tracking (`user_sessions`)
- Projects: `/api/v1/projects` + web `/projects`
- Chat: SSE streaming, session history (`chat_sessions` / `chat_messages`)
- Knowledge base: `/api/v1/knowledge` document import, pgvector semantic search (optional RAG injection)
- Trading log: CRUD + stats + AI analysis (supports `project_id` filtering)
- Reports: `/api/v1/reports` + web `/reports` (list/detail/scheduling)
- Async jobs: Celery worker/beat + `/api/v1/tasks` (report generation, KB import queue/status)
- Redis: rate limiting + short TTL caching (analysis/retrieval)
- Self-hosting: Docker Compose (db/redis/api/web/worker/beat)

### Related docs

- Self-hosted: `../aiwendy/docs/SELF_HOSTING.md`
- Deployment: `../aiwendy/docs/DEPLOYMENT.md`
- LLM config: `CUSTOM_API_SETUP.md`
