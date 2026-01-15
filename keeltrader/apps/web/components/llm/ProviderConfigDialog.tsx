'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useI18n } from '@/lib/i18n/provider'
import {
  llmConfigApi,
  type LLMProviderConfig,
  type ProviderTemplate
} from '@/lib/api/llm-config'
import { toast } from 'sonner'
import {
  Cloud,
  Server,
  Sparkles,
  TestTube,
  AlertCircle,
  Check,
  X,
  Globe,
  Key,
  Link,
  Settings,
  Zap
} from 'lucide-react'

interface ProviderConfigDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  config?: LLMProviderConfig
  onSave?: (config: LLMProviderConfig) => Promise<void>
}

const PROVIDER_ICONS: Record<string, any> = {
  openai: Sparkles,
  anthropic: Cloud,
  ollama: Server,
  custom: Globe,
  groq: Zap,
  together: Link,
  perplexity: Globe,
  deepinfra: Server,
  openrouter: Link,
  moonshot: Sparkles,
  zhipu: Sparkles,
  baichuan: Sparkles,
  qwen: Sparkles,
  deepseek: Sparkles,
  oneapi: Link,
  api2d: Link,
  vllm: Server,
  localai: Server,
  xinference: Server,
}

const COMMON_MODELS: Record<string, string[]> = {
  openai: [
    'gpt-4-turbo-preview',
    'gpt-4',
    'gpt-3.5-turbo',
    'gpt-3.5-turbo-16k',
  ],
  anthropic: [
    'claude-3-opus-20240229',
    'claude-3-sonnet-20240229',
    'claude-3-haiku-20240307',
    'claude-2.1',
  ],
  groq: [
    'mixtral-8x7b-32768',
    'llama2-70b-4096',
    'gemma-7b-it',
  ],
  together: [
    'mistralai/Mixtral-8x7B-Instruct-v0.1',
    'meta-llama/Llama-2-70b-chat-hf',
    'NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO',
  ],
  deepseek: [
    'deepseek-chat',
    'deepseek-coder',
  ],
  qwen: [
    'qwen-turbo',
    'qwen-plus',
    'qwen-max',
  ],
  zhipu: [
    'glm-4',
    'glm-3-turbo',
  ],
  moonshot: [
    'moonshot-v1-8k',
    'moonshot-v1-32k',
    'moonshot-v1-128k',
  ],
}

function choosePreferredModel(
  models: string[],
  providerType?: string,
  apiFormat?: string,
): string | undefined {
  const cleaned = models.map(m => m.trim()).filter(Boolean)
  if (cleaned.length === 0) return undefined

  const preferred =
    providerType === 'anthropic' || apiFormat === 'anthropic'
      ? ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229', 'claude-2.1']
      : providerType === 'ollama'
        ? ['llama3.2:latest', 'llama3:latest']
        : ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']

  const preferredSet = new Set(preferred)
  for (const model of cleaned) {
    if (preferredSet.has(model)) return model
  }

  const prefixes =
    providerType === 'anthropic' || apiFormat === 'anthropic'
      ? ['claude-']
      : providerType === 'ollama'
        ? ['llama']
        : ['gpt-', 'claude-', 'gemini', 'deepseek', 'qwen', 'moonshot', 'glm', 'yi', 'llama']

  for (const prefix of prefixes) {
    const match = cleaned.find(m => m.startsWith(prefix))
    if (match) return match
  }

  const nonAqa = cleaned.find(m => m.toLowerCase() !== 'aqa')
  return nonAqa || cleaned[0]
}

export function ProviderConfigDialog({
  open,
  onOpenChange,
  config,
  onSave
}: ProviderConfigDialogProps) {
  const { t, locale } = useI18n()
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null)
  const [testMessage, setTestMessage] = useState<string>('')
  const [templates, setTemplates] = useState<Record<string, ProviderTemplate>>({})
  const [availableProviders, setAvailableProviders] = useState<any>({ providers: [], presets: { cloud: [], local: [], proxy: [] } })

  const [formData, setFormData] = useState<LLMProviderConfig>({
    name: '',
    provider_type: 'openai',
    is_active: true,
    is_default: false,
    api_key: '',
    base_url: '',
    default_model: '',
    available_models: [],
    api_format: 'openai',
    auth_type: 'bearer',
    chat_endpoint: '/v1/chat/completions',
    completions_endpoint: '/v1/completions',
    embeddings_endpoint: '/v1/embeddings',
    models_endpoint: '/v1/models',
    supports_streaming: true,
    supports_functions: false,
    supports_vision: false,
    supports_embeddings: true,
    max_tokens_limit: 4096,
    ...config
  })

  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    loadTemplates()
    loadProviders()
  }, [])

  useEffect(() => {
    if (config) {
      setFormData({
        ...formData,
        ...config
      })
    }
  }, [config])

  // 重置状态当对话框关闭时
  useEffect(() => {
    if (!open) {
      setLoading(false)
      setTestResult(null)
      setTestMessage('')
    }
  }, [open])

  const loadTemplates = async () => {
    try {
      const data = await llmConfigApi.getTemplates()
      setTemplates(data.templates)
    } catch (error) {
      console.error('Failed to load templates:', error)
    }
  }

  const loadProviders = async () => {
    try {
      const data = await llmConfigApi.getAvailableProviders()
      setAvailableProviders(data)
    } catch (error) {
      console.error('Failed to load providers:', error)
    }
  }

  const applyTemplate = (templateKey: string) => {
    const template = templates[templateKey]
    if (template) {
      setFormData({
        ...formData,
        ...template,
        api_format: template.api_format as 'openai' | 'anthropic' | 'google' | 'custom' | undefined,
        auth_type: template.auth_type as 'bearer' | 'api_key' | 'basic' | 'none' | undefined,
        provider_type: 'custom'
      })
    }
  }

  const fetchModels = async () => {
    const needsBaseUrl = formData.provider_type === 'custom'
    const needsApiKey = formData.provider_type !== 'ollama' && formData.auth_type !== 'none'

    if (!formData.id) {
      if (needsBaseUrl && !formData.base_url) {
        toast.error(locale === 'zh' ? '请先输入 API 地址' : 'Please enter API URL first')
        return
      }

      if (needsApiKey && !formData.api_key) {
        toast.error(locale === 'zh' ? '请先输入 API 密钥' : 'Please enter API key first')
        return
      }
    }

    try {
      setLoading(true)
      const models = formData.id
        ? await llmConfigApi.getModelsForConfig(formData.id)
        : await llmConfigApi.fetchModels({
            provider_type: formData.provider_type,
            api_key: formData.api_key || undefined,
            base_url: formData.base_url || undefined,
            api_format: formData.api_format,
            auth_type: formData.auth_type,
            auth_header_name: formData.auth_header_name,
            models_endpoint: formData.models_endpoint,
            extra_headers: formData.extra_headers,
          })

      if (models.length > 0) {
        const currentDefault = (formData.default_model || '').trim()
        const preferred = choosePreferredModel(models, formData.provider_type, formData.api_format)
        const nextDefault =
          (currentDefault && currentDefault.toLowerCase() !== 'aqa')
            ? currentDefault
            : (preferred || currentDefault)

        setFormData({
          ...formData,
          available_models: models,
          default_model: nextDefault || ''
        })
        toast.success(locale === 'zh' ? `获取到 ${models.length} 个模型` : `Found ${models.length} models`)
      } else {
        toast.info(locale === 'zh' ? '未找到可用模型' : 'No models found')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      toast.error(message || (locale === 'zh' ? '获取模型列表失败' : 'Failed to fetch models'))
    } finally {
      setLoading(false)
    }
  }

  const testConnection = async () => {
    setTesting(true)
    setTestResult(null)
    setTestMessage('')

    try {
      if (formData.id) {
        await llmConfigApi.testConfig({
          config_id: formData.id,
          message: locale === 'zh'
            ? '你好！请简短地介绍一下自己。'
            : 'Hello! Please briefly introduce yourself.',
          model: formData.default_model || undefined,
        })
        setTestResult('success')
        setTestMessage(locale === 'zh' ? '连接成功！' : 'Connection successful!')
        return
      }

      const result = await llmConfigApi.quickTest({
        provider_type: formData.provider_type,
        api_key: formData.api_key || '',
        base_url: formData.base_url,
        model: formData.default_model || undefined
      })

      if (result.connected) {
        setTestResult('success')
        setTestMessage(locale === 'zh' ? '连接成功！' : 'Connection successful!')
      } else {
        setTestResult('error')
        setTestMessage(result.error || (locale === 'zh' ? '连接失败' : 'Connection failed'))
      }
    } catch (error: any) {
      setTestResult('error')
      setTestMessage(error.message || (locale === 'zh' ? '测试失败' : 'Test failed'))
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    if (!formData.name) {
      toast.error(locale === 'zh' ? '请输入配置名称' : 'Please enter a configuration name')
      return
    }

    if (formData.provider_type === 'custom' && !formData.base_url) {
      toast.error(locale === 'zh' ? '请输入 API 地址' : 'Please enter API URL')
      return
    }

    setLoading(true)
    try {
      // 清理数据，移除 undefined 值
      const cleanedData = Object.fromEntries(
        Object.entries(formData).filter(([_, v]) => v !== undefined)
      ) as LLMProviderConfig

      if (onSave) {
        await onSave(cleanedData)
      } else {
        if (config?.id) {
          await llmConfigApi.updateConfig(config.id, cleanedData)
        } else {
          await llmConfigApi.createConfig(cleanedData)
        }
        toast.success(locale === 'zh' ? '保存成功' : 'Saved successfully')
      }
      onOpenChange(false)
    } catch (error: any) {
      console.error('Save error:', error)
      toast.error(error.message || (locale === 'zh' ? '保存失败' : 'Failed to save'))
    } finally {
      setLoading(false)
    }
  }

  const getProviderName = (type: string) => {
    const provider = availableProviders.providers.find((p: any) => p.type === type)
    return provider?.description || type.toUpperCase()
  }

  const Icon = PROVIDER_ICONS[formData.provider_type] || Globe

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {config ? (locale === 'zh' ? '编辑配置' : 'Edit Configuration') : (locale === 'zh' ? '添加 LLM 提供商' : 'Add LLM Provider')}
          </DialogTitle>
          <DialogDescription>
            {locale === 'zh' ? '配置 AI 模型提供商连接信息' : 'Configure AI model provider connection'}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="basic" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="basic">
              {locale === 'zh' ? '基本设置' : 'Basic Settings'}
            </TabsTrigger>
            <TabsTrigger value="models">
              {locale === 'zh' ? '模型配置' : 'Model Configuration'}
            </TabsTrigger>
            <TabsTrigger value="advanced">
              {locale === 'zh' ? '高级选项' : 'Advanced Options'}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="basic" className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">{locale === 'zh' ? '配置名称' : 'Configuration Name'}</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder={locale === 'zh' ? '例如：我的 OpenAI' : 'e.g., My OpenAI'}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider">{locale === 'zh' ? '提供商类型' : 'Provider Type'}</Label>
              <Select
                value={formData.provider_type}
                onValueChange={(value) => {
                  setFormData({
                    ...formData,
                    provider_type: value,
                    default_model: COMMON_MODELS[value]?.[0] || '',
                    available_models: COMMON_MODELS[value] || []
                  })
                }}
              >
                <SelectTrigger>
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4" />
                    <SelectValue />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  {availableProviders.presets.cloud.length > 0 && (
                    <>
                      <Label className="px-2 py-1.5 text-xs text-muted-foreground">
                        {locale === 'zh' ? '云端服务' : 'Cloud Services'}
                      </Label>
                      {availableProviders.presets.cloud.map((provider: string) => {
                        const ProvIcon = PROVIDER_ICONS[provider] || Cloud
                        return (
                          <SelectItem key={provider} value={provider}>
                            <div className="flex items-center gap-2">
                              <ProvIcon className="h-4 w-4" />
                              {getProviderName(provider)}
                            </div>
                          </SelectItem>
                        )
                      })}
                    </>
                  )}
                  {availableProviders.presets.local.length > 0 && (
                    <>
                      <Label className="px-2 py-1.5 text-xs text-muted-foreground">
                        {locale === 'zh' ? '本地服务' : 'Local Services'}
                      </Label>
                      {availableProviders.presets.local.map((provider: string) => {
                        const ProvIcon = PROVIDER_ICONS[provider] || Server
                        return (
                          <SelectItem key={provider} value={provider}>
                            <div className="flex items-center gap-2">
                              <ProvIcon className="h-4 w-4" />
                              {getProviderName(provider)}
                            </div>
                          </SelectItem>
                        )
                      })}
                    </>
                  )}
                  <Label className="px-2 py-1.5 text-xs text-muted-foreground">
                    {locale === 'zh' ? '自定义' : 'Custom'}
                  </Label>
                  <SelectItem value="custom">
                    <div className="flex items-center gap-2">
                      <Settings className="h-4 w-4" />
                      {locale === 'zh' ? '自定义 API' : 'Custom API'}
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {formData.provider_type === 'custom' && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-2">
                    <p>{locale === 'zh' ? '快速应用模板：' : 'Quick templates:'}</p>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => applyTemplate('openai_compatible')}
                      >
                        OpenAI Compatible
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => applyTemplate('anthropic_compatible')}
                      >
                        Anthropic Compatible
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => applyTemplate('local_server')}
                      >
                        Local Server
                      </Button>
                    </div>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="api_key">
                API {locale === 'zh' ? '密钥' : 'Key'}
                {formData.provider_type !== 'custom' && formData.auth_type !== 'none' && (
                  <span className="text-red-500 ml-1">*</span>
                )}
              </Label>
              <Input
                id="api_key"
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                placeholder={formData.provider_type === 'openai' ? 'sk-...' : 'Enter your API key'}
              />
            </div>

            {(formData.provider_type === 'custom' || formData.provider_type === 'ollama') && (
              <div className="space-y-2">
                <Label htmlFor="base_url">
                  API {locale === 'zh' ? '地址' : 'URL'}
                  <span className="text-red-500 ml-1">*</span>
                </Label>
                <Input
                  id="base_url"
                  value={formData.base_url}
                  onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                  placeholder="https://api.example.com"
                />
              </div>
            )}

            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={testConnection}
                disabled={testing || (!formData.api_key && formData.auth_type !== 'none')}
              >
                {testing ? (
                  <>
                    <Icons.spinner className="h-4 w-4 mr-2 animate-spin" />
                    {locale === 'zh' ? '测试中...' : 'Testing...'}
                  </>
                ) : (
                  <>
                    <TestTube className="h-4 w-4 mr-2" />
                    {locale === 'zh' ? '测试连接' : 'Test Connection'}
                  </>
                )}
              </Button>

              {testResult && (
                <div className="flex items-center gap-2">
                  {testResult === 'success' ? (
                    <>
                      <Check className="h-4 w-4 text-green-500" />
                      <span className="text-sm text-green-600">{testMessage}</span>
                    </>
                  ) : (
                    <>
                      <X className="h-4 w-4 text-red-500" />
                      <span className="text-sm text-red-600">{testMessage}</span>
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="active"
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
              />
              <Label htmlFor="active">
                {locale === 'zh' ? '启用此配置' : 'Enable this configuration'}
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="default"
                checked={formData.is_default}
                onCheckedChange={(checked) => setFormData({ ...formData, is_default: checked })}
              />
              <Label htmlFor="default">
                {locale === 'zh' ? '设为默认' : 'Set as default'}
              </Label>
            </div>
          </TabsContent>

          <TabsContent value="models" className="space-y-4">
            <div className="space-y-2">
              <Label>{locale === 'zh' ? '默认模型' : 'Default Model'}</Label>
              {(formData.available_models || []).length > 0 ? (
                <Select
                  value={formData.default_model}
                  onValueChange={(value) => setFormData({ ...formData, default_model: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={locale === 'zh' ? '选择默认模型' : 'Select default model'} />
                  </SelectTrigger>
                  <SelectContent>
                    {(formData.available_models || []).map((model) => (
                      <SelectItem key={model} value={model}>
                        {model}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  value={formData.default_model}
                  onChange={(e) => setFormData({ ...formData, default_model: e.target.value })}
                  placeholder={locale === 'zh' ? '输入默认模型 (例如：gpt-4o-mini)' : 'Enter default model (e.g., gpt-4o-mini)'}
                />
              )}
            </div>

            {formData.provider_type !== 'ollama' && (
              <div className="space-y-2">
                <Label>{locale === 'zh' ? '可用模型' : 'Available Models'}</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder={locale === 'zh' ? '输入模型名称' : 'Enter model name'}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        const input = e.currentTarget
                        const value = input.value.trim()
                        if (value && !formData.available_models?.includes(value)) {
                          setFormData({
                            ...formData,
                            available_models: [...(formData.available_models || []), value],
                            default_model: formData.default_model || value
                          })
                          input.value = ''
                        }
                      }
                    }}
                  />
                  <Button
                    variant="outline"
                    onClick={fetchModels}
                    disabled={loading || (!formData.id && formData.provider_type === 'custom' && !formData.base_url)}
                  >
                    {loading ? (
                      <Icons.spinner className="h-4 w-4 animate-spin" />
                    ) : (
                      locale === 'zh' ? '获取模型' : 'Fetch Models'
                    )}
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(formData.available_models || []).map((model) => (
                    <Badge key={model} variant="secondary">
                      {model}
                      <button
                        className="ml-2 text-xs hover:text-red-500"
                        onClick={() => {
                          setFormData({
                            ...formData,
                            available_models: formData.available_models?.filter(m => m !== model)
                          })
                        }}
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label>{locale === 'zh' ? '最大 Token 限制' : 'Max Token Limit'}</Label>
              <Input
                type="number"
                value={formData.max_tokens_limit}
                onChange={(e) => setFormData({ ...formData, max_tokens_limit: parseInt(e.target.value) })}
              />
            </div>
          </TabsContent>

          <TabsContent value="advanced" className="space-y-4">
            {formData.provider_type === 'custom' && (
              <>
                <div className="space-y-2">
                  <Label>API {locale === 'zh' ? '格式' : 'Format'}</Label>
                  <Select
                    value={formData.api_format}
                    onValueChange={(value: any) => setFormData({ ...formData, api_format: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI Compatible</SelectItem>
                      <SelectItem value="anthropic">Anthropic Compatible</SelectItem>
                      <SelectItem value="google">Google Compatible</SelectItem>
                      <SelectItem value="custom">Custom Format</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>{locale === 'zh' ? '认证类型' : 'Auth Type'}</Label>
                  <Select
                    value={formData.auth_type}
                    onValueChange={(value: any) => setFormData({ ...formData, auth_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="bearer">Bearer Token</SelectItem>
                      <SelectItem value="api_key">API Key Header</SelectItem>
                      <SelectItem value="basic">Basic Auth</SelectItem>
                      <SelectItem value="none">No Auth</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {formData.auth_type === 'api_key' && (
                  <div className="space-y-2">
                    <Label>{locale === 'zh' ? '认证头名称' : 'Auth Header Name'}</Label>
                    <Input
                      value={formData.auth_header_name}
                      onChange={(e) => setFormData({ ...formData, auth_header_name: e.target.value })}
                      placeholder="x-api-key"
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label>{locale === 'zh' ? 'API 端点' : 'API Endpoints'}</Label>
                  <div className="space-y-2">
                    <Input
                      placeholder="Chat endpoint"
                      value={formData.chat_endpoint}
                      onChange={(e) => setFormData({ ...formData, chat_endpoint: e.target.value })}
                    />
                    <Input
                      placeholder="Completions endpoint"
                      value={formData.completions_endpoint}
                      onChange={(e) => setFormData({ ...formData, completions_endpoint: e.target.value })}
                    />
                    <Input
                      placeholder="Embeddings endpoint"
                      value={formData.embeddings_endpoint}
                      onChange={(e) => setFormData({ ...formData, embeddings_endpoint: e.target.value })}
                    />
                    <Input
                      placeholder="Models endpoint"
                      value={formData.models_endpoint}
                      onChange={(e) => setFormData({ ...formData, models_endpoint: e.target.value })}
                    />
                  </div>
                </div>
              </>
            )}

            <div className="space-y-4">
              <Label>{locale === 'zh' ? '功能支持' : 'Feature Support'}</Label>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="streaming"
                    checked={formData.supports_streaming}
                    onCheckedChange={(checked) => setFormData({ ...formData, supports_streaming: checked })}
                  />
                  <Label htmlFor="streaming">
                    {locale === 'zh' ? '支持流式输出' : 'Supports Streaming'}
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    id="functions"
                    checked={formData.supports_functions}
                    onCheckedChange={(checked) => setFormData({ ...formData, supports_functions: checked })}
                  />
                  <Label htmlFor="functions">
                    {locale === 'zh' ? '支持函数调用' : 'Supports Function Calling'}
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    id="vision"
                    checked={formData.supports_vision}
                    onCheckedChange={(checked) => setFormData({ ...formData, supports_vision: checked })}
                  />
                  <Label htmlFor="vision">
                    {locale === 'zh' ? '支持图像识别' : 'Supports Vision'}
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    id="embeddings"
                    checked={formData.supports_embeddings}
                    onCheckedChange={(checked) => setFormData({ ...formData, supports_embeddings: checked })}
                  />
                  <Label htmlFor="embeddings">
                    {locale === 'zh' ? '支持嵌入向量' : 'Supports Embeddings'}
                  </Label>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label>{locale === 'zh' ? '速率限制' : 'Rate Limits'}</Label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  placeholder={locale === 'zh' ? '每分钟请求数' : 'Requests per minute'}
                  value={formData.requests_per_minute || ''}
                  onChange={(e) => setFormData({ ...formData, requests_per_minute: parseInt(e.target.value) || undefined })}
                />
                <Input
                  type="number"
                  placeholder={locale === 'zh' ? '每分钟 Token 数' : 'Tokens per minute'}
                  value={formData.tokens_per_minute || ''}
                  onChange={(e) => setFormData({ ...formData, tokens_per_minute: parseInt(e.target.value) || undefined })}
                />
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {locale === 'zh' ? '取消' : 'Cancel'}
          </Button>
          <Button onClick={handleSave} disabled={loading}>
            {loading ? (
              <>
                <Icons.spinner className="h-4 w-4 mr-2 animate-spin" />
                {locale === 'zh' ? '保存中...' : 'Saving...'}
              </>
            ) : (
              locale === 'zh' ? '保存' : 'Save'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
