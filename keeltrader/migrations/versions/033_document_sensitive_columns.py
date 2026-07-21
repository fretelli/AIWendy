"""Give every production credential field an explicit security contract.

Revision ID: 033
Revises: 032
"""
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    comments = {
        "users.hashed_password": "密码单向哈希；不得返回给客户端、日志、研究上下文或 AI",
        "users.openai_api_key": "用户的 OpenAI 提供商凭据字段；无论存储编码为何均按认证秘密处理，禁止明文输出",
        "users.anthropic_api_key": "用户的 Anthropic 提供商凭据字段；无论存储编码为何均按认证秘密处理，禁止明文输出",
        "users.api_keys_encrypted": "用户第三方 API 凭据的加密集合；只能在受控服务边界内解密，不得传入 AI 上下文",
        "users.email_verification_token": "邮箱验证令牌；属于一次性认证秘密，不得记录或返回给 AI",
        "device_tokens.token": "设备推送令牌；属于用户关联的认证敏感值，不得记录或返回给 AI",
        "exchange_connections.api_key_encrypted": "交易所 API key 的加密值；只能在受控连接服务内解密，禁止输出",
        "exchange_connections.api_secret_encrypted": "交易所 API secret 的加密值；只能在受控连接服务内解密，禁止输出",
        "exchange_connections.passphrase_encrypted": "交易所连接口令的加密值；只能在受控连接服务内解密，禁止输出",
        "exchange_connections.credentials_extra": "交易所额外凭据的受保护结构；所有键值均按认证秘密处理，不得传入 AI 上下文",
        "agent_platform_model_profiles.api_key_encrypted": "模型提供商 API key 的加密值；研究 Agent 不得读取或回显明文",
        "agent_platform_model_profiles.credential_source": "凭据来源标识；仅描述受管来源，不保存或暴露凭据内容",
        "agent_platform_model_profiles.key_prefix": "API key 的非秘密识别前缀；仅用于人工辨识，不得据此推断或重建完整密钥",
        "agent_platform_mcp_servers.auth_encrypted": "MCP 服务认证材料的加密值；工具调用层只能按受控策略解密，禁止进入模型上下文",
        "trading_interventions.gate_token": "人工交易干预门禁令牌；属于授权敏感值，不得被研究 Agent 用于自动执行交易",
    }
    for target, description in comments.items():
        op.execute(f"COMMENT ON COLUMN {target} IS '{description}'")


def downgrade() -> None:
    raise RuntimeError("Migration 033 strengthens security metadata and is intentionally non-reversible")
