# AIWendy 开源 + 托管 SaaS 改造总结

## 改造概述

更多文档见：`README.md`。

AIWendy 已成功改造为支持**开源自托管**和**云托管 SaaS** 双模式的项目。通过环境变量 `DEPLOYMENT_MODE` 控制运行模式，同一代码库可以灵活部署为：

- **自托管模式（默认）**: 开源社区版，适合个人和小团队
- **云托管模式**: 托管 SaaS 服务，支持多租户、计费、企业 SSO 等功能

## 核心改动

### 1. 配置系统 (`aiwendy/apps/api/config.py`)

**新增配置项：**

```python
# 部署模式
deployment_mode: str = "self-hosted"  # 或 "cloud"

# 多租户
multi_tenancy_enabled: bool = False
tenant_isolation_strict: bool = True

# 使用分析
analytics_provider: Optional[str] = None  # "posthog", "mixpanel"
posthog_api_key: Optional[str] = None
mixpanel_token: Optional[str] = None

# 企业 SSO
enterprise_sso_enabled: bool = False
saml_enabled: bool = False
oauth_providers: list[str] = []

# 计费
billing_enabled: bool = False
stripe_api_key: Optional[str] = None
stripe_webhook_secret: Optional[str] = None
```

**新增方法：**

```python
def is_cloud_mode(self) -> bool
def is_self_hosted(self) -> bool
```

### 2. 多租户模型 (`aiwendy/apps/api/domain/tenant/`)

**新增文件：**
- `models.py` - 租户和成员模型
- `__init__.py` - 包导出

**核心模型：**

```python
class Tenant(Base):
    """租户/组织模型"""
    - 组织信息（名称、slug、logo）
    - 订阅计划和状态
    - 资源限制和使用量
    - 计费信息

class TenantMember(Base):
    """租户成员关系"""
    - 用户-租户关联
    - 角色管理（owner/admin/member/guest）
    - 邀请状态
```

### 3. 使用分析服务 (`aiwendy/apps/api/services/analytics.py`)

**功能：**
- 支持 PostHog 和 Mixpanel
- 自动检测部署模式
- 自托管模式下为 no-op
- 提供便捷的事件追踪方法

**使用示例：**

```python
from services.analytics import get_analytics

analytics = get_analytics()
analytics.track_signup(user_id, email)
analytics.track_chat_message(user_id, coach_id, length)
analytics.associate_tenant(user_id, tenant_id, tenant_name, plan)
```

### 4. 企业 SSO 服务 (`aiwendy/apps/api/services/sso.py`)

**功能：**
- SAML 2.0 支持（Okta、Azure AD、OneLogin）
- OAuth 2.0 支持（Google、GitHub、Azure、Okta）
- 自动检测部署模式
- 自托管模式下禁用

**使用示例：**

```python
from services.sso import get_sso_service

sso = get_sso_service()
if sso.is_enabled():
    saml_provider = sso.get_saml_provider()
    oauth_provider = sso.get_oauth_provider("google")
```

### 5. 环境配置文件

**新增/更新：**

1. **`.env.example`** - 更新为包含所有配置项
2. **`.env.cloud.example`** - 云模式专用配置示例
3. **`requirements.cloud.txt`** - 云模式额外依赖

### 6. 文档

**新增文档：**

1. **`DEPLOYMENT_MODES.md`** - 详细的部署模式指南
   - 模式对比
   - 配置说明
   - 迁移指南
   - 常见问题

2. **`README.md`** - 更新说明部署模式

### 7. 迁移脚本

**新增：** `aiwendy/apps/api/scripts/migrate_to_multi_tenant.py`

用于将现有自托管部署迁移到云模式：
- 创建默认租户
- 迁移现有用户
- 验证迁移结果

## 使用方式

### 自托管模式（默认）

```bash
# .env
DEPLOYMENT_MODE=self-hosted  # 或不设置

# 启动
docker compose up -d --build
```

### 云托管模式

```bash
# .env
DEPLOYMENT_MODE=cloud
MULTI_TENANCY_ENABLED=true
ANALYTICS_PROVIDER=posthog
POSTHOG_API_KEY=your_key
ENTERPRISE_SSO_ENABLED=true
BILLING_ENABLED=true
STRIPE_API_KEY=your_key

# 安装云模式依赖
pip install -r requirements.txt -r requirements.cloud.txt

# 运行迁移
python scripts/migrate_to_multi_tenant.py

# 启动
docker compose up -d --build
```

## 代码中的使用

### 检查部署模式

```python
from config import get_settings

settings = get_settings()

if settings.is_cloud_mode():
    # 云模式特有逻辑
    pass

if settings.is_self_hosted():
    # 自托管模式特有逻辑
    pass
```

### 使用分析

```python
from services.analytics import get_analytics

analytics = get_analytics()
# 自托管模式下自动变为 no-op，不会实际发送数据
analytics.track_event(user_id, "feature_used", {"feature": "chat"})
```

### 使用 SSO

```python
from services.sso import get_sso_service

sso = get_sso_service()
if sso.is_enabled():
    # SSO 逻辑
    pass
```

## 功能对比

| 功能 | 自托管模式 | 云托管模式 |
|------|-----------|-----------|
| 核心 AI 功能 | ✅ | ✅ |
| 用户认证 | ✅ | ✅ |
| 多租户隔离 | ❌ | ✅ |
| 使用分析 | ❌ | ✅ |
| 企业 SSO | ❌ | ✅ |
| 计费系统 | ❌ | ✅ |
| 资源配额 | ❌ | ✅ |

## 依赖包

### 基础依赖（两种模式都需要）

已包含在 `requirements.txt` 中

### 云模式额外依赖

```bash
pip install -r requirements.cloud.txt
```

包含：
- `posthog` / `mixpanel` - 使用分析
- `python3-saml` - SAML SSO
- `stripe` - 计费
- `prometheus-client` - 监控
- 等等

## 数据库变更

### 新增表（仅云模式使用）

1. **`tenants`** - 租户/组织表
2. **`tenant_members`** - 租户成员关系表

### 迁移

```bash
# 自动运行迁移
docker compose up -d --build

# 或手动运行
docker exec aiwendy-api alembic upgrade head
```

## 安全考虑

### 自托管模式
- 使用强密码和 JWT secret
- 定期更新依赖
- 配置防火墙和 HTTPS

### 云托管模式
- 所有自托管安全措施
- 严格租户数据隔离
- 加密敏感数据
- 定期安全审计
- 符合合规标准（SOC 2、ISO 27001）

## 下一步

### 对于自托管用户
1. 继续使用默认配置即可
2. 所有核心功能保持不变
3. 可选择性启用某些云功能（如分析）

### 对于云托管部署
1. 复制 `.env.cloud.example` 到 `.env`
2. 配置所有必需的云服务
3. 运行迁移脚本
4. 配置 Stripe webhook
5. 配置 SSO 提供商
6. 设置监控和告警

### 开发建议
1. 在添加新功能时，考虑是否需要租户隔离
2. 使用 `settings.is_cloud_mode()` 来条件性启用云功能
3. 确保自托管模式下的功能完整性
4. 为云功能编写单独的测试

## 许可证

- **自托管模式**: Apache 2.0 开源许可证
- **云托管模式**: 商业许可证（需要单独协商）

## 支持

- **自托管**: GitHub Issues 和社区支持
- **云托管**: 专业技术支持和 SLA

## 总结

通过这次改造，AIWendy 实现了：

✅ **灵活部署** - 同一代码库支持两种模式
✅ **功能完整** - 自托管版本保持核心功能完整
✅ **商业化就绪** - 云版本具备 SaaS 运营所需的所有功能
✅ **易于维护** - 通过环境变量控制，无需维护多个分支
✅ **开源友好** - 核心代码保持开源，云功能可选启用

这种架构既满足了开源社区的需求，也为商业化 SaaS 服务提供了完整的基础设施。
