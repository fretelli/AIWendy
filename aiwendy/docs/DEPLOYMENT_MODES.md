# AIWendy 部署模式指南

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

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

---

<a id="en"></a>
## English

AIWendy supports two deployment modes:

1. **Self-hosted** (Self-Hosted) — open-source Community edition, best for individuals and small teams
2. **Cloud-hosted** (Cloud/SaaS) — hosted service edition with multi-tenancy, billing, enterprise SSO, and more

### Mode comparison

| Feature | Self-hosted | Cloud-hosted |
|---|---|---|
| Deployment | Docker Compose / K8s | Managed cloud service |
| User management | Single-tenant | Multi-tenant isolation |
| Auth | Email/password / optional disabled | Email/password + enterprise SSO |
| Billing | None | Stripe integration |
| Analytics | Optional (local) | PostHog/Mixpanel |
| Data isolation | Single instance | Strict tenant isolation |
| Resource limits | None | Plan-based quotas |
| Updates | Manual | Automatic |
| Support | Community | Professional support |

## Self-hosted (default)

### Configuration

Set in `.env`:

```bash
DEPLOYMENT_MODE=self-hosted
```

Or leave it unset (default is `self-hosted`).

### Characteristics

- Fully open-source (Apache 2.0)
- Full data control
- No usage limits
- Optional “no-login” guest mode (`AIWENDY_AUTH_REQUIRED=0`)
- Supports custom LLM APIs
- No billing system
- No multi-tenant isolation
- No enterprise SSO

### Quick start

```bash
cd aiwendy
cp .env.example .env
# edit .env and fill required settings
docker compose up -d --build
```

Visit `http://localhost:3000`

### Best for

- Personal use
- Internal use by small teams
- When you need full data control
- When you don’t need billing
- When you want to customize/extend

## Cloud-hosted (SaaS)

### Configuration

Set in `.env`:

```bash
DEPLOYMENT_MODE=cloud
```

And configure additional env vars required for cloud mode (see `.env.cloud.example`).

### Characteristics

- Multi-tenant architecture with strict data isolation
- Stripe billing integration
- Analytics (PostHog/Mixpanel)
- Enterprise SSO (SAML/OAuth)
- Resource quota management
- Automatic scaling and updates
- Professional technical support

### Required configuration

#### 1. Multi-tenancy

```bash
MULTI_TENANCY_ENABLED=true
TENANT_ISOLATION_STRICT=true
```

#### 2. Analytics

```bash
ANALYTICS_PROVIDER=posthog
POSTHOG_API_KEY=phc_your_key
POSTHOG_HOST=https://app.posthog.com
```

Or Mixpanel:

```bash
ANALYTICS_PROVIDER=mixpanel
MIXPANEL_TOKEN=your_token
```

#### 3. Enterprise SSO (optional)

SAML 2.0:

```bash
ENTERPRISE_SSO_ENABLED=true
SAML_ENABLED=true
SAML_ENTITY_ID=https://api.yourdomain.com/saml/metadata
SAML_SSO_URL=https://api.yourdomain.com/saml/sso
SAML_X509_CERT=your_certificate
```

OAuth 2.0:

```bash
ENTERPRISE_SSO_ENABLED=true
OAUTH_PROVIDERS=["google", "github", "azure", "okta"]
```

#### 4. Billing (Stripe)

```bash
BILLING_ENABLED=true
STRIPE_API_KEY=sk_live_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_PRICE_ID_FREE=price_xxx
STRIPE_PRICE_ID_PRO=price_xxx
STRIPE_PRICE_ID_ENTERPRISE=price_xxx
```

### Database migrations

Cloud mode requires additional tables:

```bash
# run migrations to create tenant tables
docker exec aiwendy-api alembic upgrade head
```

### Best for

- Operating a SaaS product
- Needing strict multi-tenant isolation
- Requiring billing
- Enterprise customers needing SSO
- Wanting analytics and monitoring

## Migrating from self-hosted to cloud-hosted

If you’re already running the self-hosted version and want to migrate to cloud mode:

### 1. Back up data

```bash
docker exec aiwendy-postgres pg_dump -U aiwendy aiwendy > backup.sql
```

### 2. Update configuration

Copy `.env.cloud.example` to `.env` and configure all required cloud services.

### 3. Run migrations

```bash
# stop services
docker compose down

# update code
git pull

# start services (migrations may run automatically depending on your setup)
docker compose up -d --build

# or run migrations manually
docker exec aiwendy-api alembic upgrade head
```

### 4. Create tenants

Create tenants for existing users:

```bash
docker exec aiwendy-api python scripts/migrate_to_multi_tenant.py
```

### 5. Configure external services

- Set up Stripe webhooks
- Configure PostHog/Mixpanel
- Configure SSO providers

## Feature flags

Regardless of mode, features can be toggled via env vars:

```bash
# feature flags
FEATURE_ANALYTICS_ENABLED=true
FEATURE_MULTI_COACH_ENABLED=true
FEATURE_VOICE_ENABLED=false
FEATURE_KNOWLEDGE_BASE_ENABLED=true

# rate limits
RATE_LIMIT_ENABLED=true
RATE_LIMIT_FREE_CHAT_HOURLY=10
RATE_LIMIT_FREE_JOURNAL_DAILY=3
RATE_LIMIT_PRO_CHAT_HOURLY=100
RATE_LIMIT_PRO_JOURNAL_DAILY=999
```

## Checking deployment mode in code

```python
from config import get_settings

settings = get_settings()

# cloud mode?
if settings.is_cloud_mode():
    # cloud-specific logic
    pass

# self-hosted mode?
if settings.is_self_hosted():
    # self-hosted-specific logic
    pass

# is multi-tenancy enabled?
if settings.multi_tenancy_enabled:
    # multi-tenant logic
    pass
```

## Dependencies

### Self-hosted

Base dependencies are included in `requirements.txt`.

### Additional dependencies for cloud mode

```bash
# analytics
pip install posthog  # or mixpanel

# enterprise SSO
pip install python3-saml

# billing
pip install stripe
```

Or use a cloud-specific requirements file:

```bash
pip install -r requirements.cloud.txt
```

## Monitoring and logs

### Self-hosted

- Logs are written to `./logs`
- Optional Sentry integration

### Cloud-hosted

- Sentry is required
- PostHog/Mixpanel for analytics
- Recommended: Datadog/New Relic for infrastructure monitoring

## Security considerations

### Self-hosted

- Keep dependencies up to date
- Use strong passwords and a strong JWT secret
- Configure firewall rules
- Enable HTTPS

### Cloud-hosted

- All self-hosted security practices
- Strict tenant data isolation
- Regular security audits
- SOC 2 / ISO 27001 compliance
- Encryption in transit and at rest
- Regular backups and disaster recovery plans

## Performance optimization

### Self-hosted

- Tune `DATABASE_POOL_SIZE` based on load
- Configure Redis caching
- Use a CDN for static assets

### Cloud-hosted

- Use managed databases (RDS/Cloud SQL)
- Use managed Redis (ElastiCache/MemoryStore)
- Configure autoscaling
- Use load balancers
- Enable CDN

## Cost estimation

### Self-hosted

- Server cost (VPS/cloud VM)
- Domain and SSL certificate
- Backup storage
- Maintenance time

### Cloud-hosted

- Infrastructure (compute/storage/network)
- Third-party services (Stripe/PostHog/Sentry)
- People cost (engineering/ops/support)
- Marketing and sales

## Support

### Self-hosted

- GitHub Issues: use your fork’s Issues page
- Community forum
- Docs: `../aiwendy/docs/`

### Cloud-hosted

- Professional support
- SLA guarantees
- Priority issue handling
- Custom development support

## License

- **Self-hosted**: Apache 2.0 open-source license
- **Cloud-hosted**: commercial license (contact us for details)

## FAQ

### Q: Can I use cloud features in self-hosted mode?

A: Technically yes, but you need to integrate and operate the third-party services yourself (Stripe, PostHog, etc.). Cloud mode is designed for managed SaaS operation.

### Q: Can I export data from cloud mode?

A: Yes. Data export APIs/tools can be provided to ensure portability.

### Q: Will the self-hosted version keep getting updates?

A: Yes. Core features will continue to be updated in the open-source version, while some advanced features may be available only in cloud mode.

### Q: Can I migrate from cloud back to self-hosted?

A: Yes. Migration tools and docs can be provided to help you export data and deploy to your own servers.

### Q: Is the feature gap large between the two modes?

A: Core features (AI chat, knowledge base, trading log, reports) are the same in both modes. Cloud mode mainly adds multi-tenancy, billing, enterprise SSO, and other SaaS-operational capabilities.
