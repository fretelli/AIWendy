'use client'

import { useRef, useEffect, useState, KeyboardEvent, ClipboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Paperclip, Mic, Send, Square, Sparkles, X, Loader2 } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ImagePreview } from './ImagePreview'
import { FileAttachment } from './FileAttachment'
import { useVoiceRecorder, formatDuration } from '@/hooks/useVoiceRecorder'
import type { PendingAttachment, VoiceMode } from '@/types/chat'
import { getFileCategory } from '@/types/chat'

interface MessageInputProps {
  value: string
  onChange: (value: string) => void
  onSend: (value: string, attachments?: PendingAttachment[]) => void
  onCancel?: () => void
  isLoading?: boolean
  placeholder?: string
  className?: string
}

export function MessageInput({
  value,
  onChange,
  onSend,
  onCancel,
  isLoading = false,
  placeholder = "Type your message...",
  className = ""
}: MessageInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [attachments, setAttachments] = useState<PendingAttachment[]>([])
  const [voiceMode, setVoiceMode] = useState<VoiceMode>('transcribe')

  const {
    isRecording,
    duration,
    audioBlob,
    startRecording,
    stopRecording,
    resetRecording,
    isSupported: isVoiceSupported,
  } = useVoiceRecorder()

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [value])

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send message on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Handle paste for images
  const handlePaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items
    if (!items) return

    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (file) {
          addFileAttachment(file)
        }
        break
      }
    }
  }

  // Add file as attachment
  const addFileAttachment = (file: File) => {
    const id = `att-${Date.now()}-${Math.random().toString(36).slice(2)}`
    const type = getFileCategory(file.type, file.name)
    const previewUrl = type === 'image' ? URL.createObjectURL(file) : ''

    const attachment: PendingAttachment = {
      id,
      type,
      file,
      previewUrl,
      status: 'pending',
    }

    setAttachments((prev) => [...prev, attachment])
  }

  // Handle file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    for (const file of files) {
      addFileAttachment(file)
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Remove attachment
  const removeAttachment = (id: string) => {
    setAttachments((prev) => {
      const att = prev.find((a) => a.id === id)
      if (att?.previewUrl) {
        URL.revokeObjectURL(att.previewUrl)
      }
      return prev.filter((a) => a.id !== id)
    })
  }

  // Handle microphone click
  const handleMicClick = async () => {
    if (isRecording) {
      const blob = await stopRecording()
      if (blob) {
        if (voiceMode === 'attachment') {
          // Add as attachment
          const file = new File([blob], `recording-${Date.now()}.webm`, {
            type: blob.type || 'audio/webm',
          })
          addFileAttachment(file)
        }
        // For 'transcribe' mode, the transcription will be handled by ChatInterface
        // We need to pass the blob up somehow - for now, add as attachment
        // and let ChatInterface handle the transcription
        else {
          const file = new File([blob], `recording-${Date.now()}.webm`, {
            type: blob.type || 'audio/webm',
          })
          const id = `att-${Date.now()}-${Math.random().toString(36).slice(2)}`
          const attachment: PendingAttachment = {
            id,
            type: 'audio',
            file,
            previewUrl: URL.createObjectURL(blob),
            status: 'pending',
          }
          setAttachments((prev) => [...prev, attachment])
        }
      }
      resetRecording()
    } else {
      await startRecording()
    }
  }

  // Send message
  const handleSend = () => {
    if (isLoading) return
    if (!value.trim() && attachments.length === 0) return

    onSend(value, attachments.length > 0 ? attachments : undefined)

    // Clear attachments after send
    attachments.forEach((att) => {
      if (att.previewUrl) {
        URL.revokeObjectURL(att.previewUrl)
      }
    })
    setAttachments([])
  }

  const hasContent = value.trim() || attachments.length > 0

  return (
    <div className={`px-4 py-3 ${className}`}>
      {/* Attachment Preview Area */}
      {attachments.length > 0 && (
        <div className="max-w-4xl mx-auto mb-2">
          <div className="flex gap-2 flex-wrap p-2 bg-muted/30 rounded-lg border">
            {attachments.map((att) => (
              att.type === 'image' ? (
                <ImagePreview
                  key={att.id}
                  src={att.previewUrl}
                  alt={att.file.name}
                  onRemove={() => removeAttachment(att.id)}
                  size="sm"
                  isLoading={att.status === 'uploading'}
                />
              ) : (
                <FileAttachment
                  key={att.id}
                  fileName={att.file.name}
                  fileSize={att.file.size}
                  type={att.type}
                  onRemove={() => removeAttachment(att.id)}
                  isLoading={att.status === 'uploading'}
                  className="max-w-[200px]"
                />
              )
            ))}
          </div>
        </div>
      )}

      <div className="max-w-4xl mx-auto">
        <div className="relative flex items-end gap-2 bg-muted/50 rounded-lg border p-2">
          {/* Action Buttons (Left) */}
          <div className="flex items-center gap-1 pb-1">
            {/* File Upload */}
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              multiple
              onChange={handleFileSelect}
              accept="image/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.json,.csv,.xml,.yaml,.yml,.py,.js,.ts,.jsx,.tsx,.html,.css,.java,.c,.cpp,.go,.rs,.rb,.php"
            />
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    disabled={isLoading || isRecording}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Paperclip className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Attach file</p>
                </TooltipContent>
              </Tooltip>

              {/* Voice Recording */}
              <DropdownMenu>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant={isRecording ? "destructive" : "ghost"}
                        size="sm"
                        className="h-8 w-8 p-0"
                        disabled={isLoading || !isVoiceSupported}
                        onClick={handleMicClick}
                      >
                        {isRecording ? (
                          <Square className="h-4 w-4" />
                        ) : (
                          <Mic className="h-4 w-4" />
                        )}
                      </Button>
                    </DropdownMenuTrigger>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{isRecording ? 'Stop recording' : 'Voice input'}</p>
                  </TooltipContent>
                </Tooltip>
                {!isRecording && (
                  <DropdownMenuContent align="start">
                    <DropdownMenuItem onClick={() => setVoiceMode('transcribe')}>
                      <span className={voiceMode === 'transcribe' ? 'font-medium' : ''}>
                        Transcribe to text
                      </span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setVoiceMode('attachment')}>
                      <span className={voiceMode === 'attachment' ? 'font-medium' : ''}>
                        Send as voice
                      </span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                )}
              </DropdownMenu>
            </TooltipProvider>

            {/* Recording indicator */}
            {isRecording && (
              <span className="text-xs text-destructive animate-pulse ml-1">
                {formatDuration(duration)}
              </span>
            )}
          </div>

          {/* Textarea */}
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={isRecording ? "Recording..." : placeholder}
            disabled={isLoading || isRecording}
            className="flex-1 min-h-[40px] max-h-[200px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 px-2"
            rows={1}
            style={{ height: '40px' }}
          />

          {/* Send/Cancel Button (Right) */}
          <div className="pb-1">
            {isLoading ? (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={onCancel}
                      variant="destructive"
                      size="sm"
                      className="h-8 px-3"
                    >
                      <Square className="h-4 w-4 mr-1" />
                      Stop
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Cancel generation</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ) : (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={handleSend}
                      disabled={!hasContent || isRecording}
                      size="sm"
                      className="h-8 px-3"
                    >
                      <Send className="h-4 w-4 mr-1" />
                      Send
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Send message (Enter)</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </div>

        {/* Helper Text */}
        <div className="flex items-center justify-between mt-2 px-2">
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <Sparkles className="h-3 w-3" />
            Powered by AI • Press Enter to send, Shift+Enter for new line
          </p>
          <div className="flex items-center gap-2">
            {attachments.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {attachments.length} attachment{attachments.length > 1 ? 's' : ''}
              </p>
            )}
            {value.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {value.length} characters
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
