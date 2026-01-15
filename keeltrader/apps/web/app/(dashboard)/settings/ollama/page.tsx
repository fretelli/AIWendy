'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Server,
  Download,
  CheckCircle,
  XCircle,
  Loader2,
  HardDrive,
  Cpu,
  RefreshCw,
  MessageSquare,
  AlertCircle,
} from 'lucide-react'
import { ollamaApi, type RecommendedModel, type PullProgress } from '@/lib/api/ollama'
import { toast } from 'sonner'

export default function OllamaSettingsPage() {
  const [health, setHealth] = useState<boolean | null>(null)
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [recommendedModels, setRecommendedModels] = useState<RecommendedModel[]>([])
  const [pullingModel, setPullingModel] = useState<string | null>(null)
  const [pullProgress, setPullProgress] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [testMessage, setTestMessage] = useState('What is a good risk-reward ratio for day trading?')
  const [testingChat, setTestingChat] = useState(false)
  const [testResponse, setTestResponse] = useState<string>('')

  useEffect(() => {
    checkOllamaStatus()
    loadRecommendedModels()
  }, [])

  const checkOllamaStatus = async () => {
    setLoading(true)
    try {
      const healthStatus = await ollamaApi.checkHealth()
      setHealth(healthStatus.healthy)

      if (healthStatus.healthy) {
        const modelsResponse = await ollamaApi.listModels()
        setAvailableModels(modelsResponse.models)
        if (modelsResponse.models.length > 0) {
          setSelectedModel(modelsResponse.models[0])
        }
      }
    } catch (error) {
      console.error('Failed to check Ollama status:', error)
      setHealth(false)
    } finally {
      setLoading(false)
    }
  }

  const loadRecommendedModels = async () => {
    try {
      const response = await ollamaApi.getRecommendedModels()
      setRecommendedModels(response.models)
    } catch (error) {
      console.error('Failed to load recommended models:', error)
    }
  }

  const handlePullModel = async (modelName: string) => {
    setPullingModel(modelName)
    setPullProgress('Starting download...')

    try {
      await ollamaApi.pullModel(modelName, (progress: PullProgress) => {
        setPullProgress(progress.status)
        if (progress.done) {
          toast.success(`Model ${modelName} installed successfully!`)
          setPullingModel(null)
          setPullProgress('')
          checkOllamaStatus() // Refresh the list
        }
      })
    } catch (error) {
      toast.error(`Failed to install model: ${error}`)
      setPullingModel(null)
      setPullProgress('')
    }
  }

  const handleTestChat = async () => {
    if (!selectedModel || !testMessage.trim()) {
      toast.error('Please select a model and enter a message')
      return
    }

    setTestingChat(true)
    setTestResponse('')

    try {
      const response = await ollamaApi.testChat(selectedModel, testMessage)
      setTestResponse(response.response)
      toast.success('Chat test successful!')
    } catch (error: any) {
      toast.error(`Test failed: ${error.message}`)
    } finally {
      setTestingChat(false)
    }
  }

  const isModelInstalled = (modelName: string) => {
    return availableModels.some(m => m.startsWith(modelName.split(':')[0]))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Local Model Settings (Ollama)</h1>
        <p className="text-muted-foreground">
          Configure and manage local LLM models for offline AI coaching
        </p>
      </div>

      {/* Service Status */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            Ollama Service Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {health === true && (
                <>
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span className="text-green-500 font-medium">Service is running</span>
                  <Badge variant="outline">{availableModels.length} models installed</Badge>
                </>
              )}
              {health === false && (
                <>
                  <XCircle className="h-5 w-5 text-red-500" />
                  <span className="text-red-500 font-medium">Service is not running</span>
                </>
              )}
              {health === null && (
                <>
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                  <span className="text-yellow-500 font-medium">Unknown status</span>
                </>
              )}
            </div>
            <Button onClick={checkOllamaStatus} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>

          {health === false && (
            <Alert className="mt-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Ollama service is not running. Please install and start Ollama:
                <br />
                1. Download from <a href="https://ollama.ai" target="_blank" rel="noopener noreferrer" className="underline">ollama.ai</a>
                <br />
                2. Run: <code className="bg-muted px-1 py-0.5 rounded">ollama serve</code>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {health === true && (
        <Tabs defaultValue="models" className="space-y-4">
          <TabsList>
            <TabsTrigger value="models">Available Models</TabsTrigger>
            <TabsTrigger value="recommended">Recommended Models</TabsTrigger>
            <TabsTrigger value="test">Test Chat</TabsTrigger>
          </TabsList>

          <TabsContent value="models">
            <Card>
              <CardHeader>
                <CardTitle>Installed Models</CardTitle>
                <CardDescription>
                  Models currently available on your system
                </CardDescription>
              </CardHeader>
              <CardContent>
                {availableModels.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <HardDrive className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No models installed yet</p>
                    <p className="text-sm">Go to Recommended Models to download some</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {availableModels.map(model => (
                      <div key={model} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <Cpu className="h-5 w-5 text-muted-foreground" />
                          <div>
                            <p className="font-medium">{model}</p>
                          </div>
                        </div>
                        <Badge variant="secondary">Installed</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="recommended">
            <Card>
              <CardHeader>
                <CardTitle>Recommended Models</CardTitle>
                <CardDescription>
                  Curated models optimized for trading psychology coaching
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recommendedModels.map(model => (
                    <div key={model.name} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold">{model.name}</h3>
                            {model.recommended && (
                              <Badge variant="default" className="text-xs">Recommended</Badge>
                            )}
                            {isModelInstalled(model.name) && (
                              <Badge variant="secondary" className="text-xs">Installed</Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{model.description}</p>
                          <div className="flex items-center gap-4 text-sm">
                            <span className="text-muted-foreground">Size: {model.size}</span>
                            <span className="text-muted-foreground">Use: {model.use_case}</span>
                          </div>
                        </div>
                        <div className="ml-4">
                          {pullingModel === model.name ? (
                            <div className="text-center">
                              <Loader2 className="h-4 w-4 animate-spin mx-auto mb-2" />
                              <p className="text-xs text-muted-foreground max-w-[200px]">{pullProgress}</p>
                            </div>
                          ) : isModelInstalled(model.name) ? (
                            <Button size="sm" variant="outline" disabled>
                              <CheckCircle className="h-4 w-4 mr-2" />
                              Installed
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => handlePullModel(model.name)}
                              disabled={pullingModel !== null}
                            >
                              <Download className="h-4 w-4 mr-2" />
                              Install
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="test">
            <Card>
              <CardHeader>
                <CardTitle>Test Local Models</CardTitle>
                <CardDescription>
                  Test your installed models with a sample query
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="model">Select Model</Label>
                    <Select value={selectedModel} onValueChange={setSelectedModel}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choose a model" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableModels.map(model => (
                          <SelectItem key={model} value={model}>
                            {model}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="message">Test Message</Label>
                  <Input
                    id="message"
                    value={testMessage}
                    onChange={(e) => setTestMessage(e.target.value)}
                    placeholder="Enter a test message..."
                  />
                </div>

                <Button
                  onClick={handleTestChat}
                  disabled={!selectedModel || testingChat}
                  className="w-full md:w-auto"
                >
                  {testingChat ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <MessageSquare className="h-4 w-4 mr-2" />
                      Test Chat
                    </>
                  )}
                </Button>

                {testResponse && (
                  <div className="mt-4 p-4 bg-muted rounded-lg">
                    <p className="text-sm font-medium mb-2">Response:</p>
                    <p className="text-sm whitespace-pre-wrap">{testResponse}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}