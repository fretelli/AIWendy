# 自定义第三方 LLM / OpenAI 兼容 API 配置指南

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

AIWendy 支持为每个用户配置 LLM 提供商（含 OpenAI 兼容网关与本地模型），并在聊天/分析等能力中使用。

更多文档见：`README.md`。

## 推荐方式：在前端页面配置

进入：`/settings/llm`（设置 → LLM）

常见流程：

1. 新建配置（选择提供商、填写 `api_key`/`base_url` 等）
2. 点击测试（后端会代你调用，避免前端跨域）
3. 设为默认（后续聊天默认使用该配置）

## API 方式（适合脚本/自动化）

### 1) 查看支持的提供商

```http
GET /api/v1/llm-config/providers
```

### 2) 新建用户配置

```http
POST /api/v1/llm-config/user-configs
Content-Type: application/json

{
  "name": "My Provider",
  "provider_type": "custom",
  "api_key": "your-api-key",
  "base_url": "https://api.example.com",
  "default_model": "gpt-4o-mini",
  "api_format": "openai",
  "auth_type": "bearer",
  "chat_endpoint": "/v1/chat/completions",
  "supports_streaming": true
}
```

### 3) 测试已保存的配置

```http
POST /api/v1/llm-config/test
Content-Type: application/json

{
  "config_id": "配置ID",
  "message": "Hello, can you hear me?",
  "temperature": 0.7,
  "max_tokens": 200
}
```

### 4) 快速测试（不保存）

```http
POST /api/v1/llm-config/quick-test
Content-Type: application/json

{
  "provider_type": "groq",
  "api_key": "gsk_xxx",
  "model": "mixtral-8x7b-32768"
}
```

## 字段说明（最常用）

- `provider_type`：内置提供商类型，或使用 `"custom"`
- `api_key`：API Key（后端会加密存储）
- `base_url`：自定义/私有部署时的 API 根地址（例如 `http://localhost:11434`）
- `default_model`：默认模型名
- `api_format`（custom 时）：`openai` / `anthropic` / `google` / `custom`
- `auth_type`（custom 时）：`bearer` / `api_key` / `basic` / `none`
- `chat_endpoint` / `embeddings_endpoint` / `models_endpoint`：自定义端点路径（可选）
- `extra_headers` / `extra_body_params`：额外 Header/Body 字段（可选）

## 常见示例

### 1) 本地 Ollama

```json
{
  "name": "Local Ollama",
  "provider_type": "ollama",
  "base_url": "http://localhost:11434",
  "default_model": "llama3.2:latest"
}
```

### 2) 自建/代理的 OpenAI 兼容网关

```json
{
  "name": "OpenAI Compatible Gateway",
  "provider_type": "custom",
  "base_url": "https://your-gateway.example.com",
  "api_key": "xxx",
  "api_format": "openai",
  "auth_type": "bearer",
  "chat_endpoint": "/v1/chat/completions",
  "embeddings_endpoint": "/v1/embeddings"
}
```

## 故障排查

- 连接超时：检查 `base_url`、代理/防火墙、目标服务是否可达
- 认证失败：确认 `auth_type` 与 Header 名称是否正确
- 模型不可用：先用 `/api/v1/llm-config/models` 拉取模型列表，再设置 `default_model`

---

<a id="en"></a>
## English

AIWendy lets each user configure their own LLM provider (including OpenAI-compatible gateways and local models), and use it in chat/analysis features.

More docs: `README.md`.

### Recommended: configure in the UI

Go to: `/settings/llm` (Settings → LLM)

Typical workflow:

1. Create a config (choose provider, fill `api_key` / `base_url`, etc.)
2. Click “Test” (the backend calls on your behalf to avoid browser CORS issues)
3. Set as default (future chats use it by default)

### API approach (for scripts/automation)

#### 1) List supported providers

```http
GET /api/v1/llm-config/providers
```

#### 2) Create a user config

```http
POST /api/v1/llm-config/user-configs
Content-Type: application/json

{
  "name": "My Provider",
  "provider_type": "custom",
  "api_key": "your-api-key",
  "base_url": "https://api.example.com",
  "default_model": "gpt-4o-mini",
  "api_format": "openai",
  "auth_type": "bearer",
  "chat_endpoint": "/v1/chat/completions",
  "supports_streaming": true
}
```

#### 3) Test a saved config

```http
POST /api/v1/llm-config/test
Content-Type: application/json

{
  "config_id": "CONFIG_ID",
  "message": "Hello, can you hear me?",
  "temperature": 0.7,
  "max_tokens": 200
}
```

#### 4) Quick test (no save)

```http
POST /api/v1/llm-config/quick-test
Content-Type: application/json

{
  "provider_type": "groq",
  "api_key": "gsk_xxx",
  "model": "mixtral-8x7b-32768"
}
```

### Field notes (most common)

- `provider_type`: built-in provider type, or `"custom"`
- `api_key`: API key (stored encrypted by the backend)
- `base_url`: API base URL for custom/private deployments (e.g. `http://localhost:11434`)
- `default_model`: default model name
- `api_format` (for `custom`): `openai` / `anthropic` / `google` / `custom`
- `auth_type` (for `custom`): `bearer` / `api_key` / `basic` / `none`
- `chat_endpoint` / `embeddings_endpoint` / `models_endpoint`: custom endpoint paths (optional)
- `extra_headers` / `extra_body_params`: extra header/body fields (optional)

### Common examples

#### 1) Local Ollama

```json
{
  "name": "Local Ollama",
  "provider_type": "ollama",
  "base_url": "http://localhost:11434",
  "default_model": "llama3.2:latest"
}
```

#### 2) Self-hosted / proxied OpenAI-compatible gateway

```json
{
  "name": "OpenAI Compatible Gateway",
  "provider_type": "custom",
  "base_url": "https://your-gateway.example.com",
  "api_key": "xxx",
  "api_format": "openai",
  "auth_type": "bearer",
  "chat_endpoint": "/v1/chat/completions",
  "embeddings_endpoint": "/v1/embeddings"
}
```

### Troubleshooting

- Timeouts: check `base_url`, proxy/firewall, and whether the target service is reachable
- Auth failures: confirm `auth_type` and header naming
- Model not available: fetch models via `/api/v1/llm-config/models`, then set `default_model`

