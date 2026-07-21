"""Document the complete legacy application schema for humans and AI agents.

Revision ID: 032
Revises: 031
"""
from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            item RECORD;
            description TEXT;
        BEGIN
            COMMENT ON SCHEMA public IS 'KeelTrader 应用数据；数据库注释是供人和 AI 使用的数据字典，未明确的业务口径不得自行推断';

            FOR item IN
                SELECT c.oid, c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
                  AND obj_description(c.oid, 'pg_class') IS NULL
            LOOP
                description := CASE
                    WHEN item.relname = 'alembic_version' THEN 'Alembic 数据库迁移版本状态；不属于业务数据'
                    WHEN item.relname = 'users' THEN 'KeelTrader 用户账户、认证状态与个人基础配置'
                    WHEN item.relname = 'user_sessions' THEN '用户登录会话及撤销状态；属于安全敏感数据'
                    WHEN item.relname = 'journals' THEN '用户私有交易复盘日志；不代表券商成交事实'
                    WHEN item.relname = 'journal_templates' THEN '交易复盘日志模板'
                    WHEN item.relname = 'projects' THEN '用户研究项目及其工作区元数据'
                    WHEN item.relname = 'uploaded_files' THEN '用户上传文件的私有元数据与存储定位；不保存公开下载权限'
                    WHEN item.relname = 'exchange_connections' THEN '用户交易所连接配置；密钥字段必须加密且不得输出给 AI'
                    WHEN item.relname = 'exchange_trades' THEN '外部交易所成交记录的导入或同步副本'
                    WHEN item.relname = 'reports' THEN '用户生成或保存的研究报告元数据与正文'
                    WHEN item.relname = 'report_schedules' THEN '研究报告生成计划'
                    WHEN item.relname = 'report_templates' THEN '研究报告模板'
                    WHEN item.relname = 'notifications' THEN '用户通知消息与读取状态'
                    WHEN item.relname = 'device_tokens' THEN '用户设备推送令牌；属于安全敏感数据'
                    WHEN item.relname = 'tenants' THEN '租户组织及隔离边界'
                    WHEN item.relname = 'tenant_members' THEN '租户成员关系与角色'
                    WHEN item.relname = 'knowledge_documents' THEN '用户或租户私有知识文档元数据'
                    WHEN item.relname = 'knowledge_chunks' THEN '知识文档检索分块及向量关联信息'
                    WHEN item.relname LIKE 'agent_platform_%' THEN format('KeelTrader 单一研究 Agent 平台的 %s 数据；不得用于未经人工确认的交易执行', replace(item.relname, 'agent_platform_', ''))
                    WHEN item.relname LIKE 'agent_company_%' THEN format('用户私有公司研究工作区的 %s 数据', replace(item.relname, 'agent_company_', ''))
                    WHEN item.relname LIKE 'agent_holder_%' THEN format('用户私有股东雷达的 %s 数据', replace(item.relname, 'agent_holder_', ''))
                    WHEN item.relname LIKE 'roundtable_%' THEN format('多角色研究讨论的 %s 数据', replace(item.relname, 'roundtable_', ''))
                    WHEN item.relname LIKE 'chat_%' THEN format('研究对话的 %s 数据', replace(item.relname, 'chat_', ''))
                    WHEN item.relname LIKE 'user_%' THEN format('用户维度的 %s 数据', replace(item.relname, 'user_', ''))
                    ELSE format('KeelTrader 业务表 %s；具体边界以列注释、约束和对应领域模型为准', item.relname)
                END;
                EXECUTE format('COMMENT ON TABLE public.%I IS %L', item.relname, description);
            END LOOP;

            FOR item IN
                SELECT c.oid, c.relname, a.attname, a.attnum,
                       format_type(a.atttypid, a.atttypmod) AS data_type,
                       a.attnotnull
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid
                WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
                  AND a.attnum > 0 AND NOT a.attisdropped
                  AND col_description(c.oid, a.attnum) IS NULL
            LOOP
                description := CASE item.attname
                    WHEN 'id' THEN '记录主键'
                    WHEN 'user_id' THEN '所属用户标识；用于用户级数据隔离'
                    WHEN 'tenant_id' THEN '所属租户标识；用于租户级数据隔离'
                    WHEN 'session_id' THEN '关联会话标识'
                    WHEN 'project_id' THEN '关联研究项目标识'
                    WHEN 'created_at' THEN '记录创建时间'
                    WHEN 'updated_at' THEN '记录最后更新时间'
                    WHEN 'deleted_at' THEN '软删除时间；为空表示未删除'
                    WHEN 'expires_at' THEN '过期时间'
                    WHEN 'revoked_at' THEN '撤销时间；为空表示未撤销'
                    WHEN 'finished_at' THEN '任务完成时间'
                    WHEN 'started_at' THEN '任务开始时间'
                    WHEN 'status' THEN '业务状态；合法值以对应领域模型和 API 枚举为准'
                    WHEN 'state' THEN '状态机当前状态；合法迁移以对应领域服务为准'
                    WHEN 'kind' THEN '记录类型；合法值以对应领域模型为准'
                    WHEN 'type' THEN '记录类型；合法值以对应领域模型为准'
                    WHEN 'name' THEN '名称'
                    WHEN 'title' THEN '标题'
                    WHEN 'description' THEN '说明文本'
                    WHEN 'content' THEN '正文内容；可包含用户私有信息'
                    WHEN 'metadata' THEN '结构化扩展元数据；JSON 键以对应 API 模型为准'
                    WHEN 'payload' THEN '任务或事件的结构化载荷；JSON 键以生产者协议为准'
                    WHEN 'settings' THEN '结构化配置；JSON 键以对应领域模型为准'
                    WHEN 'config' THEN '结构化配置；敏感值不得明文存储或返回给 AI'
                    WHEN 'email' THEN '用户电子邮箱；属于个人信息'
                    WHEN 'password_hash' THEN '密码单向哈希；不得返回给客户端或 AI'
                    WHEN 'access_token' THEN '访问令牌；属于认证秘密，不得记录或返回给 AI'
                    WHEN 'refresh_token' THEN '刷新令牌；属于认证秘密，不得记录或返回给 AI'
                    WHEN 'api_key' THEN 'API 密钥密文或受保护值；不得明文输出'
                    WHEN 'secret' THEN '受保护秘密；不得明文输出'
                    WHEN 'symbol' THEN '证券、基金、期货、期权或交易品种代码'
                    WHEN 'currency' THEN '币种代码'
                    WHEN 'quantity' THEN '数量；单位由关联交易工具决定'
                    WHEN 'price' THEN '价格；币种和报价单位由关联交易工具决定'
                    WHEN 'entry_price' THEN '计划或记录的入场价格；不代表自动成交'
                    WHEN 'exit_price' THEN '计划或记录的退出价格'
                    WHEN 'stop_price' THEN '计划止损价格；不构成自动下单指令'
                    WHEN 'target_price' THEN '计划目标价格；不构成收益承诺'
                    WHEN 'pnl' THEN '盈亏金额；币种与计算口径以所属记录为准'
                    WHEN 'notional' THEN '名义本金；币种与合约乘数口径以所属工具为准'
                    WHEN 'max_loss' THEN '按记录假设估算的最大损失，不代表极端情况下的损失上限'
                    WHEN 'is_active' THEN '是否处于启用状态'
                    WHEN 'enabled' THEN '是否启用'
                    WHEN 'notes' THEN '用户私有备注'
                    ELSE format(
                        'KeelTrader 字段 %s；数据库类型 %s；%s。精确枚举、JSON 结构、金额单位或业务公式未在本注释明确时，必须以 %s 领域模型和 API 契约为准，不得自行推断',
                        item.attname,
                        item.data_type,
                        CASE WHEN item.attnotnull THEN '不可为空' ELSE '允许为空表示未知、不适用或尚未产生' END,
                        item.relname
                    )
                END;
                EXECUTE format('COMMENT ON COLUMN public.%I.%I IS %L', item.relname, item.attname, description);
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    raise RuntimeError("Migration 032 adds documentation metadata and is intentionally non-reversible")
