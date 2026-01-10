# AIWendy（Community）

AIWendy 是一个「AI 交易心理绩效教练」应用：

- Web：Next.js 14 / React / TypeScript / Tailwind + shadcn/ui
- API：FastAPI（Python 3.11+）/ SQLAlchemy
- Data：PostgreSQL（pgvector）/ Redis
- Async：Celery worker/beat（可选）

## 一键自托管（Docker Compose）

完整步骤与排错：`docs/SELF_HOSTING.md`

```bash
# 1) 复制环境变量（PowerShell）
Copy-Item .env.example .env

# 2) 启动（db + redis + api + web）
docker compose up -d --build
```

（可选）当你关闭了自动初始化时可手动执行：

```bash
docker exec aiwendy-api python scripts/init_db_simple.py
docker exec aiwendy-api python scripts/init_user_simple.py
```

访客模式默认开启（免登录）；需要登录时访问：`http://localhost:3000/auth/login`

## 文档索引

- 自托管：`docs/SELF_HOSTING.md`
- 部署：`docs/DEPLOYMENT.md`
- 架构：`docs/ARCHITECTURE.md`
- 自定义第三方 LLM / OpenAI 兼容 API：`../docs/CUSTOM_API_SETUP.md`
- 国际化（i18n）：`../docs/I18N_GUIDE.md`
- 项目状态（以代码为准）：`../docs/PROJECT_STATUS.md`
- 完整方案/设计文档：`../docs/aiwendy-full-spec.md`

## 功能概览（以代码为准）

- Projects 分组：多项目管理与隔离
- 对话：SSE 流式输出、会话历史持久化
- 知识库：文档导入 + pgvector 语义检索（RAG 可选注入）
- 交易日志：记录/统计/AI 分析
- 报告：日报/周报/月报 + 定时生成（Celery）
