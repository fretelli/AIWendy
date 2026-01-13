# 测试账号初始化（精简）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

用于开发/自测环境快速创建默认测试账号（脚本具备幂等性，已存在则跳过）。

## 默认账号

| Type | Email | Password | Tier |
|------|-------|----------|------|
| User | test@example.com | Test@1234 | Free |
| Admin | admin@aiwendy.com | Admin@123 | Elite + Admin |

## 运行方式

### Docker Compose（推荐）

多数情况下会在容器启动时自动初始化；如需手动执行：

```bash
docker exec aiwendy-api python scripts/init_user_simple.py
```

### 本地运行 API

确保数据库已启动且迁移已完成后：

```bash
python scripts/init_user_simple.py
```

## 注意

- 仅用于开发/测试环境，不要在生产环境使用默认密码

---

<a id="en"></a>
## English

Quickly create default test accounts for development/self-testing (the script is idempotent and skips if accounts already exist).

### Default accounts

| Type | Email | Password | Tier |
|------|-------|----------|------|
| User | test@example.com | Test@1234 | Free |
| Admin | admin@aiwendy.com | Admin@123 | Elite + Admin |

### How to run

#### Docker Compose (recommended)

In most cases the container startup auto-initializes; to run manually:

```bash
docker exec aiwendy-api python scripts/init_user_simple.py
```

#### Running the API locally

After the database is up and migrations are applied:

```bash
python scripts/init_user_simple.py
```

### Notes

- For development/testing only; do not use default passwords in production

