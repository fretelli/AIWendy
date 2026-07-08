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
docker compose exec -T api python scripts/init_user_simple.py
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

## 脚本边界

`docker_start.sh` 是容器入口脚本。生产环境只执行 Alembic migration；开发环境在显式启用自动初始化时会调用 `bootstrap_projects.py`、`init_db_simple.py`、`add_journal_tables.py`，并按需调用 `init_user_simple.py` 创建测试账号。

其他数据库脚本属于历史/手动维护脚本，只有在确认目标数据库、迁移状态和回滚方案后才应执行。优先使用 Alembic migrations 或 `core/bootstrap` 中的幂等 schema bootstrap，不要把一次性脚本加入生产启动路径。

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
docker compose exec -T api python scripts/init_user_simple.py
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

### Script Boundaries

`docker_start.sh` is the container entrypoint. In production it only runs Alembic migrations; in development it calls `bootstrap_projects.py`, `init_db_simple.py`, and `add_journal_tables.py` only when automatic initialization is enabled, and it may call `init_user_simple.py` for test users.

Other database scripts are legacy/manual maintenance tools. Run them only after confirming the target database, migration state, and rollback plan. Prefer Alembic migrations or the idempotent schema bootstrap in `core/bootstrap`; do not add one-off scripts to the production startup path.
