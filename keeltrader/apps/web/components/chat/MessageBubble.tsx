'use client'

import { useState, useEffect, type CSSProperties } from 'react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Icons } from '@/components/icons'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import type { Message } from '@/types/chat'
import { Copy, Check, User, Bot, Trash2, Pencil, RefreshCcw } from 'lucide-react'
import { ImagePreview } from './ImagePreview'
import { FileAttachment } from './FileAttachment'

interface MessageBubbleProps {
  message: Message
  onDelete?: () => void
  onEdit?: () => void
  onRegenerate?: () => void
  className?: string
}

export function MessageBubble({
  message,
  onDelete,
  onEdit,
  onRegenerate,
  className = "",
}: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  const [displayedContent, setDisplayedContent] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  // Typing animation effect
  useEffect(() => {
    if (isAssistant && message.isStreaming && message.content) {
      setDisplayedContent(message.content)
      setIsTyping(true)
    } else if (isAssistant && !message.isStreaming) {
      setDisplayedContent(message.content)
      setIsTyping(false)
    } else {
      setDisplayedContent(message.content)
    }
  }, [message.content, message.isStreaming, isAssistant])

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedCode(id)
      setTimeout(() => setCopiedCode(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div
      className={cn(
        'group relative flex gap-4',
        isUser && 'flex-row-reverse',
        className
      )}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        <Avatar className={cn(
          "h-8 w-8",
          isUser ? "bg-primary" : "bg-gradient-to-br from-purple-600 to-blue-500"
        )}>
          {isUser ? (
            <>
              <AvatarImage src="/avatar-placeholder.png" alt="You" />
              <AvatarFallback className="bg-primary text-primary-foreground">
                <User className="h-4 w-4" />
              </AvatarFallback>
            </>
          ) : isAssistant ? (
            <>
              <AvatarImage src="/wendy-avatar.png" alt="Wendy" />
              <AvatarFallback className="text-white">
                <Bot className="h-4 w-4" />
              </AvatarFallback>
            </>
          ) : (
            <AvatarFallback>S</AvatarFallback>
          )}
        </Avatar>
      </div>

      {/* Message Content */}
      <div className={cn(
        'flex-1 space-y-2',
        isUser && 'flex flex-col items-end'
      )}>
        {/* Name and Time */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-medium">
            {isUser ? 'You' : isAssistant ? 'Wendy' : 'System'}
          </span>
          <span>
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
          {message.error && (
            <span className="text-destructive">Error</span>
          )}
        </div>

        {/* Message Body */}
        <div
          className={cn(
            'relative rounded-lg px-4 py-3',
            isUser
              ? 'bg-primary text-primary-foreground max-w-[80%]'
              : 'bg-muted max-w-full',
            message.error && 'border border-destructive'
          )}
        >
          {!message.isStreaming && (
            <div
              className={cn(
                "absolute right-1 top-1 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity",
                isUser
                  ? "text-primary-foreground/80"
                  : "text-muted-foreground"
              )}
            >
              {isUser && onEdit && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-7 w-7",
                    isUser
                      ? "hover:text-primary-foreground hover:bg-primary/20"
                      : "hover:text-foreground hover:bg-muted/80"
                  )}
                  onClick={onEdit}
                  aria-label="Edit message"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              )}

              <Button
                type="button"
                variant="ghost"
                size="icon"
                className={cn(
                  "h-7 w-7",
                  isUser
                    ? "hover:text-primary-foreground hover:bg-primary/20"
                    : "hover:text-foreground hover:bg-muted/80"
                )}
                onClick={() => copyToClipboard(message.content, `copy-${message.id}`)}
                disabled={!message.content}
                aria-label="Copy message"
              >
                {copiedCode === `copy-${message.id}` ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>

              {isAssistant && onRegenerate && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-7 w-7",
                    isUser
                      ? "hover:text-primary-foreground hover:bg-primary/20"
                      : "hover:text-foreground hover:bg-muted/80"
                  )}
                  onClick={onRegenerate}
                  aria-label="Regenerate message"
                >
                  <RefreshCcw className="h-4 w-4" />
                </Button>
              )}

              {onDelete && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-7 w-7",
                    isUser
                      ? "hover:text-primary-foreground hover:bg-primary/20"
                      : "hover:text-foreground hover:bg-muted/80"
                  )}
                  onClick={onDelete}
                  aria-label="Delete message"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          )}
          {/* Attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {message.attachments.map((att) => (
                att.type === 'image' ? (
                  <ImagePreview
                    key={att.id}
                    src={att.url}
                    alt={att.fileName}
                    size="md"
                  />
                ) : (
                  <FileAttachment
                    key={att.id}
                    fileName={att.fileName}
                    fileSize={att.fileSize}
                    type={att.type}
                    url={att.url}
                    transcription={att.transcription}
                    extractedText={att.extractedText}
                    showPreview
                    className="max-w-[250px]"
                  />
                )
              ))}
            </div>
          )}

          {message.isStreaming && !displayedContent ? (
            <div className="flex items-center gap-2">
              <Icons.loader2 className="h-3 w-3 animate-spin" />
              <span className="text-sm animate-pulse">Thinking...</span>
            </div>
          ) : isAssistant ? (
            <div className={cn(
              "prose prose-sm dark:prose-invert max-w-none",
              isTyping && "animate-pulse"
            )}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => (
                    <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>
                  ),
                  ul: ({ children }) => (
                    <ul className="mb-3 ml-6 list-disc last:mb-0 space-y-1">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="mb-3 ml-6 list-decimal last:mb-0 space-y-1">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="mb-1">{children}</li>
                  ),
                  h1: ({ children }) => (
                    <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-lg font-semibold mb-3 mt-4 first:mt-0">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-semibold mb-2 mt-3 first:mt-0">{children}</h3>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-primary/50 pl-4 italic my-3">
                      {children}
                    </blockquote>
                  ),
                  code: ({ className, children, ...props }) => {
                    const match = /language-(\w+)/.exec(className || '')
                    const codeString = String(children).replace(/\n$/, '')
                    const codeId = `code-${Date.now()}-${Math.random()}`

                    return match ? (
                      <div className="relative group/code my-3">
                        <div className="absolute right-2 top-2 opacity-0 group-hover/code:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2"
                            onClick={() => copyToClipboard(codeString, codeId)}
                          >
                            {copiedCode === codeId ? (
                              <Check className="h-3 w-3" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </Button>
                        </div>
                        <SyntaxHighlighter
                          style={oneDark as Record<string, CSSProperties>}
                          language={match[1]}
                          PreTag="div"
                          className="rounded-md text-sm"
                        >
                          {codeString}
                        </SyntaxHighlighter>
                      </div>
                    ) : (
                      <code className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono" {...props}>
                        {children}
                      </code>
                    )
                  },
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      className="text-primary underline decoration-primary/50 underline-offset-2 hover:decoration-primary transition-colors"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {children}
                    </a>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3">
                      <table className="min-w-full divide-y divide-border">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-muted/50">{children}</thead>
                  ),
                  th: ({ children }) => (
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-3 py-2 text-sm">{children}</td>
                  ),
                }}
              >
                {displayedContent}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="text-sm whitespace-pre-wrap break-words">
              {displayedContent}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
