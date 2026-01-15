'use client'

import { useState, useEffect, useRef } from 'react'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import {
  Settings,
  Cpu,
  Cloud,
  Sparkles,
  Server,
  ChevronDown,
  Globe,
  Zap,
  Link,
  AlertCircle,
} from 'lucide-react'
import { ollamaApi } from '@/lib/api/ollama'
import { llmConfigApi, type LLMProviderConfig } from '@/lib/api/llm-config'
import { toast } from 'sonner'
import { useI18n } from '@/lib/i18n/provider'

export interface ModelConfig {
  provider: string  // Changed from strict type to string to support any provider
  configId?: string  // Add config ID to track which configuration is being used
  model: string
  temperature: number
  maxTokens: number
  stream: boolean
}

interface ModelSelectorProps {
  config: ModelConfig
  onConfigChange: (config: ModelConfig) => void
}

// Provider icons mapping
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

export function ModelSelector({ config, onConfigChange }: ModelSelectorProps) {
  const { t, locale } = useI18n()
  const [userConfigs, setUserConfigs] = useState<LLMProviderConfig[]>([])
  const [loadingConfigs, setLoadingConfigs] = useState(true)
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [ollamaAvailable, setOllamaAvailable] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [modelsByConfigId, setModelsByConfigId] = useState<Record<string, string[]>>({})
  const [modelSearch, setModelSearch] = useState('')
  const [modelSelectOpen, setModelSelectOpen] = useState(false)
  const modelSearchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadUserConfigs()
    checkOllamaModels()
  }, [])

  useEffect(() => {
    if (!modelSelectOpen) return
    setModelSearch('')
    window.setTimeout(() => modelSearchRef.current?.focus(), 0)
  }, [modelSelectOpen])

  useEffect(() => {
    const configId = config.configId
    if (!configId) return

    const currentConfig = userConfigs.find(c => c.id === configId)
    if (!currentConfig) return

    if (currentConfig.provider_type === 'ollama') return
    if (modelsByConfigId[configId]) return

    let cancelled = false
    ;(async () => {
      try {
        const models = await llmConfigApi.getModelsForConfig(configId)
        if (!cancelled) {
          setModelsByConfigId(prev => ({ ...prev, [configId]: models }))
        }
      } catch (error) {
        console.error('Failed to load models for config:', error)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [config.configId, userConfigs, modelsByConfigId])

  useEffect(() => {
    const configId = config.configId
    if (!configId) return

    const currentConfig = userConfigs.find(c => c.id === configId)
    if (!currentConfig) return

    if (config.model) return

    const dynamicModels = currentConfig.id ? modelsByConfigId[currentConfig.id] : undefined
    const availableModels =
      (dynamicModels && dynamicModels.length > 0)
        ? dynamicModels
        : (currentConfig.available_models && currentConfig.available_models.length > 0)
          ? currentConfig.available_models
          : (currentConfig.provider_type === 'ollama')
            ? ollamaModels
            : []

    const defaultModel = currentConfig.default_model?.trim()
    const preferred = choosePreferredModel(availableModels, currentConfig.provider_type, currentConfig.api_format)
    const nextModel = defaultModel || preferred
    if (!nextModel) return

    onConfigChange({
      ...config,
      model: nextModel,
    })
  }, [config.configId, config.model, modelsByConfigId, ollamaModels, onConfigChange, userConfigs])

  const loadUserConfigs = async () => {
    try {
      const configs = await llmConfigApi.getUserConfigs()
      // Only show active configurations
      const activeConfigs = configs.filter(c => c.is_active)
      setUserConfigs(activeConfigs)

      // If there's a default config and no current selection, use it
      const defaultConfig = activeConfigs.find(c => c.is_default)
      if (defaultConfig && !config.configId) {
        const preferred = choosePreferredModel(
          defaultConfig.available_models || [],
          defaultConfig.provider_type,
          defaultConfig.api_format,
        )
        onConfigChange({
          ...config,
          provider: defaultConfig.provider_type,
          configId: defaultConfig.id,
          model: defaultConfig.default_model || preferred || config.model,
        })
      }
    } catch (error) {
      console.error('Failed to load user configurations:', error)
    } finally {
      setLoadingConfigs(false)
    }
  }

  const checkOllamaModels = async () => {
    try {
      const health = await ollamaApi.checkHealth()
      if (health.healthy) {
        const response = await ollamaApi.listModels()
        setOllamaModels(response.models)
        setOllamaAvailable(response.available)
      }
    } catch (error) {
      console.error('Failed to check Ollama models:', error)
    }
  }

  const handleConfigChange = (configId: string) => {
    // Handle special case for "manage" option
    if (configId === 'manage') {
      window.location.href = '/settings/llm'
      return
    }

    const selectedConfig = userConfigs.find(c => c.id === configId)
    if (selectedConfig) {
      const preferred = choosePreferredModel(
        selectedConfig.available_models || [],
        selectedConfig.provider_type,
        selectedConfig.api_format,
      )
      onConfigChange({
        ...config,
        provider: selectedConfig.provider_type,
        configId: selectedConfig.id,
        model: selectedConfig.default_model || preferred || '',
      })
    }
  }

  const handleModelChange = (model: string) => {
    onConfigChange({
      ...config,
      model,
    })

    const current = getCurrentConfig()
    if (!current?.id) return
    if (current.default_model === model) return

    ;(async () => {
      try {
        await llmConfigApi.updateConfig(current.id!, {
          ...current,
          default_model: model,
        })
        setUserConfigs(prev =>
          prev.map(cfg =>
            cfg.id === current.id ? { ...cfg, default_model: model } : cfg
          )
        )
        toast.success(locale === 'zh' ? '已设为默认模型' : 'Set as default model')
      } catch (error: any) {
        toast.error(error?.message || (locale === 'zh' ? '设置默认模型失败' : 'Failed to set default model'))
      }
    })()
  }

  const getProviderIcon = (provider: string) => {
    const Icon = PROVIDER_ICONS[provider] || Cpu
    return <Icon className="h-4 w-4" />
  }

  const getProviderLabel = (config: LLMProviderConfig) => {
    return config.name
  }

  const getCurrentConfig = () => {
    return userConfigs.find(c => c.id === config.configId)
  }

  const getCurrentModelName = () => {
    const currentConfig = getCurrentConfig()
    if (!currentConfig) return 'Select Model'

    // For configurations with available models list
    if (currentConfig.available_models && currentConfig.available_models.length > 0) {
      return config.model || currentConfig.default_model || 'Select Model'
    }

    // For Ollama
    if (currentConfig.provider_type === 'ollama') {
      return config.model || 'Select Model'
    }

    return config.model || currentConfig.default_model || 'Select Model'
  }

  const getAvailableModels = () => {
    const currentConfig = getCurrentConfig()
    if (!currentConfig) return []

    const dynamicModels = currentConfig.id ? modelsByConfigId[currentConfig.id] : undefined
    if (dynamicModels && dynamicModels.length > 0) {
      return dynamicModels
    }

    // Return the available models from the configuration
    if (currentConfig.available_models && currentConfig.available_models.length > 0) {
      return currentConfig.available_models
    }

    // For Ollama, return detected models
    if (currentConfig.provider_type === 'ollama') {
      return ollamaModels
    }

    return []
  }

  // Show loading state or no configs message
  if (loadingConfigs) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Settings className="h-4 w-4 animate-spin" />
        {locale === 'zh' ? '加载配置中...' : 'Loading configurations...'}
      </div>
    )
  }

  if (userConfigs.length === 0) {
    return (
      <div className="flex items-center gap-2">
        <AlertCircle className="h-4 w-4 text-yellow-500" />
        <span className="text-sm text-muted-foreground">
          {locale === 'zh' ? '没有可用的模型配置' : 'No model configurations available'}
        </span>
        <Button
          size="sm"
          variant="outline"
          onClick={() => window.location.href = '/settings/llm'}
        >
          {locale === 'zh' ? '添加配置' : 'Add Configuration'}
        </Button>
      </div>
    )
  }

  const currentConfig = getCurrentConfig()
  const availableModels = getAvailableModels()
  const q = modelSearch.trim().toLowerCase()
  const filteredModels = q
    ? availableModels.filter((m) => m.toLowerCase().includes(q))
    : availableModels

  return (
    <div className="flex items-center gap-2">
      {/* Provider/Configuration Selector */}
      <Select value={config.configId || ''} onValueChange={handleConfigChange}>
        <SelectTrigger className="w-[200px]">
          <div className="flex items-center gap-2">
            {currentConfig && getProviderIcon(currentConfig.provider_type)}
            <SelectValue placeholder={locale === 'zh' ? '选择配置' : 'Select Configuration'}>
              {currentConfig?.name || (locale === 'zh' ? '选择配置' : 'Select Configuration')}
            </SelectValue>
          </div>
        </SelectTrigger>
        <SelectContent>
          {userConfigs.length > 0 && (
            <SelectGroup>
              <SelectLabel>{locale === 'zh' ? '可用配置' : 'Available Configurations'}</SelectLabel>
              {userConfigs.map((cfg) => {
                const Icon = PROVIDER_ICONS[cfg.provider_type] || Globe
                return (
                  <SelectItem key={cfg.id} value={cfg.id || ''}>
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4" />
                        <span>{cfg.name}</span>
                      </div>
                      {cfg.is_default && (
                        <Badge variant="secondary" className="ml-2 text-xs">
                          {locale === 'zh' ? '默认' : 'Default'}
                        </Badge>
                      )}
                    </div>
                  </SelectItem>
                )
              })}
            </SelectGroup>
          )}
          <SelectGroup>
            <SelectItem value="manage" className="text-primary">
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                {locale === 'zh' ? '管理配置...' : 'Manage Configurations...'}
              </div>
            </SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>

      {/* Model Selector */}
      {currentConfig && (
        <Select
          value={config.model}
          onValueChange={handleModelChange}
          open={modelSelectOpen}
          onOpenChange={setModelSelectOpen}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder={locale === 'zh' ? '选择模型' : 'Select model'}>
              {getCurrentModelName()}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <div className="p-2">
              <Input
                ref={modelSearchRef}
                value={modelSearch}
                onChange={(e) => setModelSearch(e.target.value)}
                onKeyDown={(e) => e.stopPropagation()}
                placeholder={locale === 'zh' ? '搜索模型...' : 'Search models...'}
              />
            </div>
            {availableModels.length > 0 ? (
              <SelectGroup>
                <SelectLabel>{locale === 'zh' ? '可用模型' : 'Available Models'}</SelectLabel>
                {filteredModels.length > 0 ? (
                  filteredModels.map(model => (
                    <SelectItem key={model} value={model}>
                      <div className="flex items-center justify-between w-full">
                        <span>{model}</span>
                        {model === currentConfig.default_model && (
                          <Badge variant="outline" className="ml-2 text-xs">
                            {locale === 'zh' ? '默认' : 'Default'}
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="__no_match__" disabled>
                    {locale === 'zh' ? '没有匹配的模型' : 'No matching models'}
                  </SelectItem>
                )}
              </SelectGroup>
            ) : (
              <div className="p-4 text-center text-sm text-muted-foreground">
                {locale === 'zh' ? '没有可用的模型' : 'No models available'}
                {currentConfig.provider_type === 'ollama' && (
                  <>
                    <br />
                    <a href="/settings/ollama" className="text-primary underline">
                      {locale === 'zh' ? '安装模型 →' : 'Install models →'}
                    </a>
                  </>
                )}
              </div>
            )}
          </SelectContent>
        </Select>
      )}

      {/* Settings Popover */}
      <Popover open={showSettings} onOpenChange={setShowSettings}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="icon">
            <Settings className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80">
          <div className="grid gap-4">
            <div className="space-y-2">
              <h4 className="font-medium leading-none">Model Settings</h4>
              <p className="text-sm text-muted-foreground">
                Fine-tune the model behavior
              </p>
            </div>

            <div className="grid gap-3">
              {/* Temperature */}
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="temperature">Temperature</Label>
                  <span className="text-sm text-muted-foreground">
                    {config.temperature}
                  </span>
                </div>
                <Slider
                  id="temperature"
                  min={0}
                  max={2}
                  step={0.1}
                  value={[config.temperature]}
                  onValueChange={([value]) =>
                    onConfigChange({ ...config, temperature: value })
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Higher values make output more creative
                </p>
              </div>

              {/* Max Tokens */}
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="maxTokens">Max Tokens</Label>
                  <span className="text-sm text-muted-foreground">
                    {config.maxTokens}
                  </span>
                </div>
                <Slider
                  id="maxTokens"
                  min={100}
                  max={4000}
                  step={100}
                  value={[config.maxTokens]}
                  onValueChange={([value]) =>
                    onConfigChange({ ...config, maxTokens: value })
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Maximum length of the response
                </p>
              </div>

              {/* Streaming */}
              <div className="flex items-center justify-between">
                <div className="grid gap-0.5">
                  <Label htmlFor="stream">Stream Response</Label>
                  <p className="text-xs text-muted-foreground">
                    Show response as it&apos;s generated
                  </p>
                </div>
                <Switch
                  id="stream"
                  checked={config.stream}
                  onCheckedChange={(checked) =>
                    onConfigChange({ ...config, stream: checked })
                  }
                />
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
