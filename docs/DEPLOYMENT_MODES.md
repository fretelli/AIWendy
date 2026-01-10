# AIWendy 部署模式指南

AIWendy 支持两种部署模式：

1. **自托管模式（Self-Hosted）** - 开源社区版，适合个人和小团队
2. **云托管模式（Cloud/SaaS）** - 托管服务版，提供多租户、计费、企业 SSO 等功能

## 部署模式对比

| 特性 | 自托管模式 | 云托管模式 |
|------|-----------|-----------|
| 部署方式 | Docker Compose / K8s | 托管云服务 |
| 用户管理 | 单租户 | 多租户隔离 |
| 认证方式 | 邮箱密码 / 可选禁用 | 邮箱密码 + 企业 SSO |
| 计费系统 | 无 | Stripe 集成 |
| 使用分析 | 可选（本地） | PostHog/Mixpanel |
| 数据隔离 | 单实例 | 严格租户隔离 |
| 资源限制 | 无限制 | 按计划配额 |
| 更新方式 | 手动更新 | 自动更新 |
| 支持方式 | 社区支持 | 专业技术支持 |

## 自托管模式（默认）

### 配置

在 `.env` 文件中设置：

```bash
DEPLOYMENT_MODE=self-hosted
```

或者不设置（默认为 self-hosted）。

### 特点

- ✅ 完全开源，Apache 2.0 许可证
- ✅ 数据完全自主控制
- ✅ 无使用限制
- ✅ 可选禁用登录认证（`AIWENDY_AUTH_REQUIRED=0`）
- ✅ 支持自定义 LLM API
- ❌ 不包含计费功能
- ❌ 不包含多租户隔离
- ❌ 不包含企业 SSO

### 快速开始

```bash
cd aiwendy
cp .env.example .env
# 编辑 .env 设置必要的配置
docker compose up -d --build
```

访问 `http://localhost:3000`

### 适用场景

- 个人使用
- 小团队内部使用
- 需要完全数据控制
- 不需要计费功能
- 希望自定义和扩展

## 云托管模式（SaaS）

### 配置

在 `.env` 文件中设置：

```bash
DEPLOYMENT_MODE=cloud
```

并配置云模式所需的额外环境变量（参考 `.env.cloud.example`）。

### 特点

- ✅ 多租户架构，严格数据隔离
- ✅ Stripe 计费集成
- ✅ 使用分析（PostHog/Mixpanel）
- ✅ 企业 SSO（SAML/OAuth）
- ✅ 资源配额管理
- ✅ 自动扩展和更新
- ✅ 专业技术支持

### 必需配置

#### 1. 多租户

```bash
MULTI_TENANCY_ENABLED=true
TENANT_ISOLATION_STRICT=true
```

#### 2. 使用分析

```bash
ANALYTICS_PROVIDER=posthog
POSTHOG_API_KEY=phc_your_key
POSTHOG_HOST=https://app.posthog.com
```

或使用 Mixpanel：

```bash
ANALYTICS_PROVIDER=mixpanel
MIXPANEL_TOKEN=your_token
```

#### 3. 企业 SSO（可选）

SAML 2.0：

```bash
ENTERPRISE_SSO_ENABLED=true
SAML_ENABLED=true
SAML_ENTITY_ID=https://api.yourdomain.com/saml/metadata
SAML_SSO_URL=https://api.yourdomain.com/saml/sso
SAML_X509_CERT=your_certificate
```

OAuth 2.0：

```bash
ENTERPRISE_SSO_ENABLED=true
OAUTH_PROVIDERS=["google", "github", "azure", "okta"]
```

#### 4. 计费（Stripe）

```bash
BILLING_ENABLED=true
STRIPE_API_KEY=sk_live_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_PRICE_ID_FREE=price_xxx
STRIPE_PRICE_ID_PRO=price_xxx
STRIPE_PRICE_ID_ENTERPRISE=price_xxx
```

### 数据库迁移

云模式需要额外的数据库表：

```bash
# 运行迁移以创建租户表
docker exec aiwendy-api alembic upgrade head
```

### 适用场景

- 提供 SaaS 服务
- 需要多租户隔离
- 需要计费功能
- 企业客户需要 SSO
- 需要使用分析和监控

## 从自托管迁移到云托管

如果你已经在运行自托管版本，想要迁移到云托管模式：

### 1. 备份数据

```bash
docker exec aiwendy-postgres pg_dump -U aiwendy aiwendy > backup.sql
```

### 2. 更新配置

复制 `.env.cloud.example` 到 `.env` 并配置所有必需的云服务。

### 3. 运行迁移

```bash
# 停止服务
docker compose down

# 更新代码
git pull

# 启动服务（会自动运行迁移）
docker compose up -d --build

# 或手动运行迁移
docker exec aiwendy-api alembic upgrade head
```

### 4. 创建租户

为现有用户创建租户：

```bash
docker exec aiwendy-api python scripts/migrate_to_multi_tenant.py
```

### 5. 配置外部服务

- 设置 Stripe webhook
- 配置 PostHog/Mixpanel
- 配置 SSO 提供商

## 功能开关

无论哪种模式，都可以通过环境变量控制功能：

```bash
# 功能开关
FEATURE_ANALYTICS_ENABLED=true
FEATURE_MULTI_COACH_ENABLED=true
FEATURE_VOICE_ENABLED=false
FEATURE_KNOWLEDGE_BASE_ENABLED=true

# 速率限制
RATE_LIMIT_ENABLED=true
RATE_LIMIT_FREE_CHAT_HOURLY=10
RATE_LIMIT_FREE_JOURNAL_DAILY=3
RATE_LIMIT_PRO_CHAT_HOURLY=100
RATE_LIMIT_PRO_JOURNAL_DAILY=999
```

## 代码中检查部署模式

在代码中可以通过配置检查当前部署模式：

```python
from config import get_settings

settings = get_settings()

# 检查是否为云模式
if settings.is_cloud_mode():
    # 云模式特有逻辑
    pass

# 检查是否为自托管模式
if settings.is_self_hosted():
    # 自托管模式特有逻辑
    pass

# 检查多租户是否启用
if settings.multi_tenancy_enabled:
    # 多租户逻辑
    pass
```

## 依赖包

### 自托管模式

基础依赖已包含在 `requirements.txt` 中。

### 云托管模式额外依赖

```bash
# 使用分析
pip install posthog  # 或 mixpanel

# 企业 SSO
pip install python3-saml

# 计费
pip install stripe
```

或使用云模式专用的 requirements 文件：

```bash
pip install -r requirements.cloud.txt
```

## 监控和日志

### 自托管模式

- 日志输出到 `./logs` 目录
- 可选集成 Sentry

### 云托管模式

- 必须配置 Sentry
- 集成 PostHog/Mixpanel 进行用户行为分析
- 推荐使用 Datadog/New Relic 进行基础设施监控

## 安全考虑

### 自托管模式

- 定期更新依赖包
- 使用强密码和 JWT secret
- 配置防火墙规则
- 启用 HTTPS

### 云托管模式

- 所有自托管模式的安全措施
- 严格的租户数据隔离
- 定期安全审计
- 符合 SOC 2/ISO 27001 标准
- 数据加密（传输和静态）
- 定期备份和灾难恢复计划

## 性能优化

### 自托管模式

- 根据负载调整 `DATABASE_POOL_SIZE`
- 配置 Redis 缓存
- 使用 CDN 加速静态资源

### 云托管模式

- 使用托管数据库（RDS/Cloud SQL）
- 使用托管 Redis（ElastiCache/MemoryStore）
- 配置自动扩展
- 使用负载均衡器
- 启用 CDN

## 成本估算

### 自托管模式

- 服务器成本（VPS/云主机）
- 域名和 SSL 证书
- 备份存储
- 维护时间成本

### 云托管模式

- 基础设施成本（计算、存储、网络）
- 第三方服务成本（Stripe、PostHog、Sentry）
- 人力成本（开发、运维、支持）
- 营销和销售成本

## 支持

### 自托管模式

- GitHub Issues：请使用你 fork 后的仓库 Issues 页面
- 社区论坛
- 文档：`../aiwendy/docs/`

### 云托管模式

- 专业技术支持
- SLA 保证
- 优先问题处理
- 定制开发支持

## 许可证

- **自托管模式**: Apache 2.0 开源许可证
- **云托管模式**: 商业许可证（联系我们获取详情）

## 常见问题

### Q: 可以在自托管模式下使用云功能吗？

A: 技术上可以，但需要自行配置和集成第三方服务（Stripe、PostHog 等）。云功能主要是为托管 SaaS 设计的。

### Q: 云模式的数据可以导出吗？

A: 可以。我们提供数据导出 API 和工具，确保数据可移植性。

### Q: 自托管版本会持续更新吗？

A: 是的。核心功能会持续开源更新，但某些高级功能可能仅在云版本提供。

### Q: 可以从云版本迁移回自托管吗？

A: 可以。我们提供迁移工具和文档，帮助你导出数据并部署到自己的服务器。

### Q: 两种模式的功能差异大吗？

A: 核心功能（AI 对话、知识库、交易日志、报告）在两种模式下完全相同。云模式主要增加了多租户、计费、企业 SSO 等 SaaS 运营所需的功能。
