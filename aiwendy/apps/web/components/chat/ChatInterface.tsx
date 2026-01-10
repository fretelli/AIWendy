'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { ModelSelector, type ModelConfig } from './ModelSelector'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Icons } from '@/components/icons'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { AlertCircle, Trash2, Download } from 'lucide-react'
import { API_V1_PREFIX } from '@/lib/config'
import { getAuthHeaders } from '@/lib/api/auth'
import type {
  Message,
  PendingAttachment,
  ChatAttachment,
  ApiMessageAttachment
} from '@/types/chat'
import { canExtractText, isImageForVision } from '@/types/chat'

// Re-export Message type for backwards compatibility
export type { Message }

/**
 * Upload a file to the server
 */
async function uploadFile(file: File): Promise<{
  id: string
  fileName: string
  fileSize: number
  mimeType: string
  type: string
  url: string
  thumbnailBase64?: string
}> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_V1_PREFIX}/files/upload`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to upload file')
  }

  return response.json()
}

/**
 * Extract text from a document file
 */
async function extractText(file: File): Promise<{ text: string } | null> {
  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_V1_PREFIX}/files/extract`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    })

    if (!response.ok) return null
    const data = await response.json()
    return data.success ? { text: data.text } : null
  } catch {
    return null
  }
}

/**
 * Transcribe audio to text
 */
async function transcribeAudio(file: File): Promise<{ text: string } | null> {
  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_V1_PREFIX}/files/transcribe`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    })

    if (!response.ok) return null
    const data = await response.json()
    return { text: data.text }
  } catch {
    return null
  }
}

/**
 * Convert a File to base64 data URL
 */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

/**
 * Process pending attachments: upload, extract text, transcribe audio
 */
async function processAttachments(
  attachments: PendingAttachment[]
): Promise<{ uploaded: ChatAttachment[]; apiAttachments: ApiMessageAttachment[] }> {
  const uploaded: ChatAttachment[] = []
  const apiAttachments: ApiMessageAttachment[] = []

  for (const att of attachments) {
    try {
      // Upload file
      const result = await uploadFile(att.file)

      // Build base attachment
      const chatAttachment: ChatAttachment = {
        id: result.id,
        type: att.type,
        fileName: result.fileName,
        fileSize: result.fileSize,
        mimeType: result.mimeType,
        url: result.url,
        thumbnailUrl: result.type === 'image' ? att.previewUrl : undefined,
      }

      const apiAttachment: ApiMessageAttachment = {
        id: result.id,
        type: att.type,
        fileName: result.fileName,
        fileSize: result.fileSize,
        mimeType: result.mimeType,
        url: result.url,
      }

      // For images, get base64 for LLM
      if (isImageForVision(att.type)) {
        apiAttachment.base64Data = await fileToBase64(att.file)
      }

      // For documents, extract text
      if (canExtractText(att.type)) {
        const extracted = await extractText(att.file)
        if (extracted) {
          chatAttachment.extractedText = extracted.text
          apiAttachment.extractedText = extracted.text
        }
      }

      // For audio, transcribe
      if (att.type === 'audio') {
        const transcribed = await transcribeAudio(att.file)
        if (transcribed) {
          chatAttachment.transcription = transcribed.text
          apiAttachment.transcription = transcribed.text
        }
      }

      uploaded.push(chatAttachment)
      apiAttachments.push(apiAttachment)
    } catch (error) {
      console.error(`Failed to process attachment ${att.file.name}:`, error)
      // Continue with other attachments
    }
  }

  return { uploaded, apiAttachments }
}

interface ChatInterfaceProps {
  coachId?: string
  sessionId?: string | null
  initialMessages?: Message[]
  placeholder?: string
  className?: string
  onNewChat?: () => void
}

export function ChatInterface({
  coachId = 'default',
  sessionId = null,
  initialMessages = [],
  placeholder = "Type your message...",
  className = "",
  onNewChat,
}: ChatInterfaceProps) {
  const createMessageId = () => `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const messagesRef = useRef<Message[]>(initialMessages)
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    provider: '',
    configId: undefined,
    model: '',
    temperature: 0.7,
    maxTokens: 2000,
    stream: true
  })
  const [useKnowledgeBase, setUseKnowledgeBase] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  const clearChat = useCallback(() => {
    if (onNewChat) {
      onNewChat()
      return
    }
    setMessages([])
    setError(null)
  }, [onNewChat])

  const exportChat = useCallback(() => {
    const chatContent = messages.map(m =>
      `[${m.timestamp.toLocaleString()}] ${m.role.toUpperCase()}: ${m.content}`
    ).join('\n\n')

    const blob = new Blob([chatContent], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `chat_export_${new Date().toISOString()}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }, [messages])

  const sendConversation = async (
    conversationMessages: Message[],
    newAttachments?: ApiMessageAttachment[]
  ) => {
    if (conversationMessages.length === 0 || isLoading) return

    setError(null)
    setIsLoading(true)

    const assistantMessage: Message = {
      id: createMessageId(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    }

    setMessages([...conversationMessages, assistantMessage])

    try {
      abortControllerRef.current = new AbortController()

      // Build messages for API, including attachments for the last message if provided
      const apiMessages = conversationMessages.map((m, index) => {
        const isLastMessage = index === conversationMessages.length - 1
        const messageAttachments = isLastMessage && newAttachments ? newAttachments : undefined

        return {
          role: m.role,
          content: m.content,
          attachments: messageAttachments,
        }
      })

      const response = await fetch(`${API_V1_PREFIX}/chat`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          coach_id: coachId,
          session_id: sessionId || undefined,
          messages: apiMessages,
          stream: modelConfig.stream,
          use_knowledge_base: useKnowledgeBase && !!sessionId,
          knowledge_top_k: useKnowledgeBase ? 5 : 0,
          config_id: modelConfig.configId,  // Pass the configuration ID
          provider: modelConfig.provider || undefined,
          model: modelConfig.model || undefined,
          temperature: modelConfig.temperature,
          max_tokens: modelConfig.maxTokens
        }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        let detail = response.statusText
        try {
          const data = await response.json()
          if (data?.detail) detail = data.detail
          else if (typeof data?.error === 'string') detail = data.error
          else if (typeof data?.message === 'string') detail = data.message
        } catch {
          // ignore
        }
        throw new Error(`Failed to send message: ${detail}`)
      }

      const contentType = response.headers.get('content-type') || ''

      // Non-streaming response
      if (!modelConfig.stream || contentType.includes('application/json')) {
        const data = await response.json()
        const text = typeof data?.response === 'string' ? data.response : JSON.stringify(data)
        setMessages(prev => prev.map(msg =>
          msg.id === assistantMessage.id ? { ...msg, content: text, isStreaming: false } : msg
        ))
        return
      }

      if (!response.body) {
        throw new Error('No response body')
      }

      // Process streaming response (SSE)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulatedContent = ''
      let buffer = ''
      let streamDone = false

      while (!streamDone) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        buffer = buffer.replace(/\r\n/g, '\n')

        let boundaryIndex = buffer.indexOf('\n\n')
        while (boundaryIndex !== -1) {
          const rawEvent = buffer.slice(0, boundaryIndex)
          buffer = buffer.slice(boundaryIndex + 2)

          for (const rawLine of rawEvent.split('\n')) {
            const line = rawLine.trim()
            if (!line.startsWith('data:')) continue

            const data = line.slice(5).trim()
            if (!data) continue

            if (data === '[DONE]') {
              streamDone = true
              break
            }

            let parsed: any
            try {
              parsed = JSON.parse(data)
            } catch {
              continue
            }

            if (parsed?.error) {
              throw new Error(parsed.error)
            }

            if (parsed?.done) {
              streamDone = true
              break
            }

            if (parsed?.content) {
              accumulatedContent += parsed.content
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === assistantMessage.id
                    ? { ...msg, content: accumulatedContent }
                    : msg
                )
              )
            }
          }

          if (streamDone) break
          boundaryIndex = buffer.indexOf('\n\n')
        }
      }

      // Mark streaming as complete
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessage.id
            ? { ...msg, isStreaming: false }
            : msg
        )
      )

    } catch (error: any) {
      console.error('Chat error:', error)

      const isNetworkError =
        error instanceof TypeError &&
        typeof error.message === 'string' &&
        (error.message.includes('NetworkError') || error.message.includes('Failed to fetch'))

      // Helper function to get user-friendly error message
      const getErrorMessage = () => {
        if (error.name === 'AbortError') {
          return 'Message canceled.'
        }

        if (isNetworkError) {
          return 'Network error: unable to reach the API server. Check that the backend is running and the API URL/proxy is configured.'
        }

        const errorMsg = error.message || 'Failed to get response'

        // Check for common error patterns and provide helpful messages
        if (errorMsg.includes('API key') || errorMsg.includes('api_key')) {
          return 'Error: Invalid or missing API key. Please configure LLM providers in Settings → LLM Configuration.'
        }

        if (errorMsg.includes('quota') || errorMsg.includes('rate limit') || errorMsg.includes('rate_limit')) {
          return 'Error: API quota exceeded or rate limited. Please try again later or switch to a different provider in the model selector.'
        }

        if (errorMsg.includes('All providers failed') || errorMsg.includes('all providers')) {
          return 'Error: All LLM providers failed. Please check your LLM provider configuration and API keys in Settings → LLM Configuration.'
        }

        if (errorMsg.includes('No LLM providers configured')) {
          return 'Error: No LLM providers configured. Please add at least one LLM provider in Settings → LLM Configuration.'
        }

        if (errorMsg.includes('Session not found') || errorMsg.includes('404')) {
          return 'Error: Chat session not found. Please create a new chat session.'
        }

        if (errorMsg.includes('Failed to retrieve messages') || errorMsg.includes('500')) {
          return 'Error: Failed to load chat history. Please try refreshing the page or creating a new session.'
        }

        return errorMsg
      }

      const errorMessage = getErrorMessage()
      const assistantContent =
        error.name === 'AbortError' ? errorMessage : `Error: ${errorMessage}`

      // Update assistant message with error
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessage.id
            ? {
                ...msg,
                content: assistantContent,
                isStreaming: false,
                error: true
              }
            : msg
        )
      )

      setError(errorMessage || 'Failed to send message')
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleSend = async (content: string, pendingAttachments?: PendingAttachment[]) => {
    const trimmed = content.trim()
    const hasAttachments = pendingAttachments && pendingAttachments.length > 0

    // Need content or attachments
    if (!trimmed && !hasAttachments) return
    if (isLoading) return

    setInputValue('')

    // Process attachments if any
    let uploadedAttachments: ChatAttachment[] = []
    let apiAttachments: ApiMessageAttachment[] = []

    if (hasAttachments) {
      try {
        const processed = await processAttachments(pendingAttachments)
        uploadedAttachments = processed.uploaded
        apiAttachments = processed.apiAttachments
      } catch (error) {
        console.error('Failed to process attachments:', error)
        setError('Failed to upload attachments')
        return
      }
    }

    const allMessages = messagesRef.current

    if (editingMessageId) {
      const editIndex = allMessages.findIndex(m => m.id === editingMessageId)
      const toEdit = editIndex >= 0 ? allMessages[editIndex] : undefined

      setEditingMessageId(null)

      if (toEdit?.role === 'user' && editIndex >= 0) {
        const editedMessage: Message = {
          ...toEdit,
          content: trimmed,
          timestamp: new Date(),
          error: false,
          isStreaming: false,
          attachments: uploadedAttachments.length > 0 ? uploadedAttachments : toEdit.attachments,
        }

        const conversation = [...allMessages.slice(0, editIndex), editedMessage]
        await sendConversation(conversation, apiAttachments)
        return
      }
    }

    const userMessage: Message = {
      id: createMessageId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
      attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
    }

    await sendConversation([...allMessages, userMessage], apiAttachments)
  }

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }

  const handleDeleteMessage = (messageId: string) => {
    if (isLoading) return
    setMessages(prev => prev.filter(m => m.id !== messageId))
    if (editingMessageId === messageId) {
      setEditingMessageId(null)
    }
  }

  const handleEditMessage = (messageId: string) => {
    if (isLoading) return
    const msg = messagesRef.current.find(m => m.id === messageId)
    if (!msg || msg.role !== 'user') return
    setEditingMessageId(messageId)
    setInputValue(msg.content)
  }

  const handleRegenerateMessage = async (messageId: string) => {
    if (isLoading) return
    const all = messagesRef.current
    const index = all.findIndex(m => m.id === messageId)
    if (index < 0) return
    const msg = all[index]
    if (msg.role !== 'assistant') return

    const conversation = all.slice(0, index)
    await sendConversation(conversation)
  }

  return (
    <div className={`flex flex-col h-full bg-background ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-4">
          <ModelSelector
            config={modelConfig}
            onConfigChange={setModelConfig}
          />
          <div className="flex items-center gap-2">
            <Switch
              id="use-kb"
              checked={useKnowledgeBase}
              onCheckedChange={setUseKnowledgeBase}
              disabled={!sessionId}
            />
            <Label htmlFor="use-kb" className="text-sm text-muted-foreground cursor-pointer">
              {sessionId ? 'KB' : 'KB (session required)'}
            </Label>
          </div>
          <span className="text-sm text-muted-foreground">
            {messages.length} messages
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={exportChat}
            disabled={messages.length === 0}
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearChat}
            disabled={messages.length === 0}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mx-4 mt-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList
          messages={messages}
          onDeleteMessage={handleDeleteMessage}
          onEditMessage={handleEditMessage}
          onRegenerateMessage={handleRegenerateMessage}
        />
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t bg-background">
        <MessageInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          onCancel={handleCancel}
          isLoading={isLoading}
          placeholder={placeholder}
        />
      </div>
    </div>
  )
}
