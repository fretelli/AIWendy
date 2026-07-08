# 测试账号初始化（精简）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

用于开发/自测环境快速创建默认测试账号（脚本具备幂等性，已存在则跳过）。

## 默认账号

脚本只提供默认邮箱和权限层级，密码必须通过环境变量显式提供：

| Type | Email | Password env | Tier |
|------|-------|--------------|------|
| User | test@example.com | `KEELTRADER_DEV_USER_PASSWORD` | Free |
| Admin | admin@keeltrader.com | `KEELTRADER_DEV_ADMIN_PASSWORD` | Elite + Admin |

## 运行方式

### Docker Compose（推荐）

多数情况下会在容器启动时自动初始化；如需手动执行：

```bash
export KEELTRADER_DEV_USER_PASSWORD='choose-a-local-dev-password'
export KEELTRADER_DEV_ADMIN_PASSWORD='choose-a-local-admin-password'
docker exec keeltrader-api python scripts/init_user_simple.py
```

### 本地运行 API

确保数据库已启动且迁移已完成后：

```bash
export KEELTRADER_DEV_USER_PASSWORD='choose-a-local-dev-password'
export KEELTRADER_DEV_ADMIN_PASSWORD='choose-a-local-admin-password'
python scripts/init_user_simple.py
```

## 注意

- 仅用于开发/测试环境；生产环境不要启用自动测试账号初始化
- 密码不会写在源码或文档里，必须由本地环境变量提供

---

<a id="en"></a>
## English

Quickly create default test accounts for development/self-testing (the script is idempotent and skips if accounts already exist).

### Default accounts

The script provides default emails and tiers only. Passwords must be supplied explicitly through environment variables:

| Type | Email | Password env | Tier |
|------|-------|--------------|------|
| User | test@example.com | `KEELTRADER_DEV_USER_PASSWORD` | Free |
| Admin | admin@keeltrader.com | `KEELTRADER_DEV_ADMIN_PASSWORD` | Elite + Admin |

### How to run

#### Docker Compose (recommended)

In most cases the container startup auto-initializes; to run manually:

```bash
export KEELTRADER_DEV_USER_PASSWORD='choose-a-local-dev-password'
export KEELTRADER_DEV_ADMIN_PASSWORD='choose-a-local-admin-password'
docker exec keeltrader-api python scripts/init_user_simple.py
```

#### Running the API locally

After the database is up and migrations are applied:

```bash
export KEELTRADER_DEV_USER_PASSWORD='choose-a-local-dev-password'
export KEELTRADER_DEV_ADMIN_PASSWORD='choose-a-local-admin-password'
python scripts/init_user_simple.py
```

### Notes

- For development/testing only; do not enable test-account initialization in production
- Passwords are not stored in source or docs and must come from local environment variables
