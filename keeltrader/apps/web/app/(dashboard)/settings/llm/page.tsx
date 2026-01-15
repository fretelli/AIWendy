'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { useI18n } from '@/lib/i18n/provider'
import { useAuth } from '@/lib/auth-context'
import { toast } from 'sonner'
import { ProviderConfigDialog } from '@/components/llm/ProviderConfigDialog'
import {
  llmConfigApi,
  type LLMProviderConfig,
} from '@/lib/api/llm-config'
import {
  Plus,
  Edit,
  Trash2,
  Settings,
  Cloud,
  Server,
  Sparkles,
  Globe,
  Zap,
  Link,
  Check,
  X,
  TestTube,
  Star,
  AlertCircle,
  ExternalLink,
  Key,
} from 'lucide-react'

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

const PROVIDER_DOCS: Record<string, string> = {
  openai: 'https://platform.openai.com/api-keys',
  anthropic: 'https://console.anthropic.com/account/keys',
  groq: 'https://console.groq.com/keys',
  together: 'https://api.together.xyz/settings/api-keys',
  perplexity: 'https://docs.perplexity.ai/docs/getting-started',
  deepinfra: 'https://deepinfra.com/dash/api_keys',
  openrouter: 'https://openrouter.ai/keys',
  moonshot: 'https://platform.moonshot.cn/console/api-keys',
  zhipu: 'https://open.bigmodel.cn/usercenter/apikeys',
  baichuan: 'https://platform.baichuan-ai.com/console/apikey',
  qwen: 'https://dashscope.console.aliyun.com/apiKey',
  deepseek: 'https://platform.deepseek.com/api_keys',
}

export default function LLMSettingsPage() {
  const router = useRouter()
  const { t, locale } = useI18n()
  const { user, isLoading: authLoading } = useAuth()
  const [loading, setLoading] = useState(true)
  const [configs, setConfigs] = useState<LLMProviderConfig[]>([])
  const [selectedConfig, setSelectedConfig] = useState<LLMProviderConfig | undefined>()
  const [showConfigDialog, setShowConfigDialog] = useState(false)
  const [deleteConfig, setDeleteConfig] = useState<LLMProviderConfig | null>(null)
  const [testing, setTesting] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      router.push('/auth/login')
      return
    }
    fetchConfigs()
  }, [authLoading, router, user])

  const fetchConfigs = async () => {
    try {
      const data = await llmConfigApi.getUserConfigs()
      setConfigs(data)
    } catch (error) {
      console.error('Failed to fetch configs:', error)
      toast.error(locale === 'zh' ? '加载配置失败' : 'Failed to load configurations')
    } finally {
      setLoading(false)
    }
  }

  const handleAddConfig = () => {
    setSelectedConfig(undefined)
    setShowConfigDialog(true)
  }

  const handleEditConfig = (config: LLMProviderConfig) => {
    setSelectedConfig(config)
    setShowConfigDialog(true)
  }

  const handleDeleteConfig = async () => {
    if (!deleteConfig?.id) return

    try {
      await llmConfigApi.deleteConfig(deleteConfig.id)
      toast.success(locale === 'zh' ? '删除成功' : 'Deleted successfully')
      fetchConfigs()
    } catch (error: any) {
      toast.error(error.message || (locale === 'zh' ? '删除失败' : 'Failed to delete'))
    } finally {
      setDeleteConfig(null)
    }
  }

  const handleTestConfig = async (config: LLMProviderConfig) => {
    if (!config.id) return

    setTesting(config.id)
    try {
      const result = await llmConfigApi.testConfig({
        config_id: config.id,
        message: locale === 'zh' ? '你好！请简短地介绍一下自己。' : 'Hello! Please briefly introduce yourself.',
      })

      if (result.status === 'success') {
        toast.success(
          <div>
            <p className="font-medium">{locale === 'zh' ? '测试成功' : 'Test successful'}</p>
            <p className="text-sm text-muted-foreground mt-1">
              {result.model} - {result.latency_ms || 0}ms
            </p>
          </div>
        )
      }
    } catch (error: any) {
      toast.error(error.message || (locale === 'zh' ? '测试失败' : 'Test failed'))
    } finally {
      setTesting(null)
    }
  }

  const handleToggleActive = async (config: LLMProviderConfig) => {
    if (!config.id) return

    try {
      await llmConfigApi.updateConfig(config.id, {
        ...config,
        is_active: !config.is_active,
      })
      toast.success(locale === 'zh' ? '状态已更新' : 'Status updated')
      fetchConfigs()
    } catch (error: any) {
      toast.error(error.message || (locale === 'zh' ? '更新失败' : 'Failed to update'))
    }
  }

  const handleSetDefault = async (config: LLMProviderConfig) => {
    if (!config.id) return

    try {
      await llmConfigApi.updateConfig(config.id, {
        ...config,
        is_default: true,
      })
      toast.success(locale === 'zh' ? '已设为默认' : 'Set as default')
      fetchConfigs()
    } catch (error: any) {
      toast.error(error.message || (locale === 'zh' ? '设置失败' : 'Failed to set default'))
    }
  }

  const handleSaveConfig = async (config: LLMProviderConfig) => {
    try {
      console.log('handleSaveConfig called', { selectedConfig, config })
      if (selectedConfig?.id) {
        await llmConfigApi.updateConfig(selectedConfig.id, config)
      } else {
        await llmConfigApi.createConfig(config)
      }
      toast.success(locale === 'zh' ? '保存成功' : 'Saved successfully')
      await fetchConfigs()
    } catch (error: any) {
      console.error('Save config error:', error)
      throw error // 重新抛出让 ProviderConfigDialog 处理
    }
  }

  const getProviderName = (type: string) => {
    const names: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      ollama: 'Ollama',
      custom: locale === 'zh' ? '自定义' : 'Custom',
      groq: 'Groq',
      together: 'Together AI',
      perplexity: 'Perplexity',
      deepinfra: 'DeepInfra',
      openrouter: 'OpenRouter',
      moonshot: 'Moonshot AI',
      zhipu: '智谱清言',
      baichuan: '百川智能',
      qwen: '通义千问',
      deepseek: 'DeepSeek',
      oneapi: 'OneAPI',
      api2d: 'API2D',
      vllm: 'vLLM',
      localai: 'LocalAI',
      xinference: 'Xinference',
    }
    return names[type] || type.toUpperCase()
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Icons.spinner className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  const Icon = PROVIDER_ICONS[selectedConfig?.provider_type || 'custom'] || Globe

  return (
    <div className="container mx-auto py-8 max-w-6xl">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">{locale === 'zh' ? 'LLM 模型配置' : 'LLM Model Configuration'}</h1>
            <p className="text-muted-foreground mt-2">
              {locale === 'zh'
                ? '管理您的 AI 模型提供商，支持 OpenAI、Anthropic 以及任何兼容的 API 接口'
                : 'Manage your AI model providers, supporting OpenAI, Anthropic, and any compatible API'}
            </p>
          </div>
          <Button onClick={handleAddConfig}>
            <Plus className="h-4 w-4 mr-2" />
            {locale === 'zh' ? '添加配置' : 'Add Configuration'}
          </Button>
        </div>
      </div>

      {configs.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Settings className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold mb-2">
              {locale === 'zh' ? '还没有配置' : 'No Configurations Yet'}
            </h3>
            <p className="text-muted-foreground mb-4">
              {locale === 'zh'
                ? '添加您的第一个 LLM 提供商配置以开始使用多模型功能'
                : 'Add your first LLM provider configuration to start using multi-model features'}
            </p>
            <Button onClick={handleAddConfig}>
              <Plus className="h-4 w-4 mr-2" />
              {locale === 'zh' ? '添加第一个配置' : 'Add First Configuration'}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <Alert className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {locale === 'zh'
                ? '您可以配置多个 LLM 提供商，并在聊天界面中自由切换。支持 OpenAI、Anthropic 以及任何兼容 OpenAI 格式的 API。'
                : 'You can configure multiple LLM providers and switch between them in the chat interface. Supports OpenAI, Anthropic, and any OpenAI-compatible API.'}
            </AlertDescription>
          </Alert>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {configs.map((config) => {
              const ProviderIcon = PROVIDER_ICONS[config.provider_type] || Globe
              const docsUrl = PROVIDER_DOCS[config.provider_type]

              return (
                <Card key={config.id} className="relative">
                  {config.is_default && (
                    <Badge className="absolute -top-2 -right-2 z-10" variant="default">
                      <Star className="h-3 w-3 mr-1" />
                      {locale === 'zh' ? '默认' : 'Default'}
                    </Badge>
                  )}
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10">
                          <ProviderIcon className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{config.name}</CardTitle>
                          <CardDescription className="text-xs mt-1">
                            {getProviderName(config.provider_type)}
                          </CardDescription>
                        </div>
                      </div>
                      <Switch
                        checked={config.is_active}
                        onCheckedChange={() => handleToggleActive(config)}
                      />
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2 text-sm">
                      <Key className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">
                        {config.api_key
                          ? (locale === 'zh' ? '已配置' : 'Configured')
                          : (locale === 'zh' ? '未配置' : 'Not configured')}
                      </span>
                      {config.api_key && (
                        <Check className="h-3 w-3 text-green-500" />
                      )}
                    </div>

                    {config.base_url && (
                      <div className="flex items-center gap-2 text-sm">
                        <Link className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground truncate" title={config.base_url}>
                          {config.base_url}
                        </span>
                      </div>
                    )}

                    {config.default_model && (
                      <div className="flex items-center gap-2 text-sm">
                        <Sparkles className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground">
                          {config.default_model}
                        </span>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-1">
                      {config.supports_streaming && (
                        <Badge variant="secondary" className="text-xs">
                          {locale === 'zh' ? '流式' : 'Stream'}
                        </Badge>
                      )}
                      {config.supports_functions && (
                        <Badge variant="secondary" className="text-xs">
                          {locale === 'zh' ? '函数' : 'Functions'}
                        </Badge>
                      )}
                      {config.supports_vision && (
                        <Badge variant="secondary" className="text-xs">
                          {locale === 'zh' ? '视觉' : 'Vision'}
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                  <CardFooter className="flex justify-between gap-2">
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleEditConfig(config)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleTestConfig(config)}
                        disabled={testing === config.id || !config.is_active}
                      >
                        {testing === config.id ? (
                          <Icons.spinner className="h-4 w-4 animate-spin" />
                        ) : (
                          <TestTube className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setDeleteConfig(config)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                    {!config.is_default && config.is_active && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleSetDefault(config)}
                      >
                        {locale === 'zh' ? '设为默认' : 'Set Default'}
                      </Button>
                    )}
                    {docsUrl && (
                      <Button
                        size="sm"
                        variant="ghost"
                        asChild
                      >
                        <a href={docsUrl} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    )}
                  </CardFooter>
                </Card>
              )
            })}
          </div>

          <div className="mt-8">
            <Card>
              <CardHeader>
                <CardTitle>{locale === 'zh' ? '快速入门' : 'Quick Start'}</CardTitle>
                <CardDescription>
                  {locale === 'zh'
                    ? '常用 LLM 提供商的快速配置指南'
                    : 'Quick setup guide for popular LLM providers'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <h4 className="font-medium mb-2">OpenAI</h4>
                    <ol className="text-sm text-muted-foreground space-y-1">
                      <li>1. {locale === 'zh' ? '访问' : 'Visit'} <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">OpenAI Platform</a></li>
                      <li>2. {locale === 'zh' ? '创建新的 API Key' : 'Create a new API key'}</li>
                      <li>3. {locale === 'zh' ? '复制并添加到配置中' : 'Copy and add to configuration'}</li>
                    </ol>
                  </div>
                  <div>
                    <h4 className="font-medium mb-2">Anthropic Claude</h4>
                    <ol className="text-sm text-muted-foreground space-y-1">
                      <li>1. {locale === 'zh' ? '访问' : 'Visit'} <a href="https://console.anthropic.com/account/keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Anthropic Console</a></li>
                      <li>2. {locale === 'zh' ? '生成 API Key' : 'Generate API key'}</li>
                      <li>3. {locale === 'zh' ? '选择 Anthropic 类型并配置' : 'Select Anthropic type and configure'}</li>
                    </ol>
                  </div>
                  <div>
                    <h4 className="font-medium mb-2">{locale === 'zh' ? '自定义 API' : 'Custom API'}</h4>
                    <ol className="text-sm text-muted-foreground space-y-1">
                      <li>1. {locale === 'zh' ? '选择"自定义 API"类型' : 'Select "Custom API" type'}</li>
                      <li>2. {locale === 'zh' ? '输入 API 地址和密钥' : 'Enter API URL and key'}</li>
                      <li>3. {locale === 'zh' ? '选择 API 格式（OpenAI 兼容等）' : 'Select API format (OpenAI compatible, etc.)'}</li>
                    </ol>
                  </div>
                  <div>
                    <h4 className="font-medium mb-2">{locale === 'zh' ? '本地模型' : 'Local Models'}</h4>
                    <ol className="text-sm text-muted-foreground space-y-1">
                      <li>1. {locale === 'zh' ? '安装 Ollama 或 vLLM' : 'Install Ollama or vLLM'}</li>
                      <li>2. {locale === 'zh' ? '启动本地服务' : 'Start local service'}</li>
                      <li>3. {locale === 'zh' ? '配置 localhost 地址' : 'Configure localhost URL'}</li>
                    </ol>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <ProviderConfigDialog
        open={showConfigDialog}
        onOpenChange={setShowConfigDialog}
        config={selectedConfig}
        onSave={handleSaveConfig}
      />

      <AlertDialog open={!!deleteConfig} onOpenChange={() => setDeleteConfig(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {locale === 'zh' ? '确认删除' : 'Confirm Delete'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {locale === 'zh'
                ? `确定要删除配置 "${deleteConfig?.name}" 吗？此操作不可恢复。`
                : `Are you sure you want to delete the configuration "${deleteConfig?.name}"? This action cannot be undone.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>
              {locale === 'zh' ? '取消' : 'Cancel'}
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfig}>
              {locale === 'zh' ? '删除' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}