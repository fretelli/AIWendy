# AIWendy Phase 2 功能实现摘要（以代码为准）

> 说明：早期文档里有“100% 完成”的表述并不等于功能已完成端到端验证；请以 `../PROJECT_STATUS.md` 与实际代码为准。

## Phase 2 覆盖的主要能力

- 多教练系统：教练列表/详情、会话与消息持久化、前端选择器
- 报告系统：日报/周报/月报生成、列表/详情、定时设置（可走异步任务）
- 订阅/支付基础链路：计划页/结算页/订阅页与后端接口（需要 Stripe 配置）

## 初始化与体验（本地）

1. 初始化 Phase 2 数据（Windows）：

```bash
.\aiwendy\scripts\init_phase2.bat
```

2. 启动服务（在 `aiwendy/` 目录）：

```bash
docker compose up -d --build
```

3. 功能入口（示例）：

- 教练：`http://localhost:3000/coaches`
- 报告：`http://localhost:3000/reports`
- 订阅：`http://localhost:3000/pricing`

## Stripe 说明

支付链路需要配置 Stripe 密钥与 webhook，并在数据库补齐订阅计划的 Price ID。详见：`STRIPE_SETUP.md`。

