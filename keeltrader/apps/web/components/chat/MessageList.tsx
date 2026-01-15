'use client'

import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble } from './MessageBubble'
import type { Message } from './ChatInterface'
import { MessageSquare, Sparkles } from 'lucide-react'

interface MessageListProps {
  messages: Message[]
  onDeleteMessage?: (messageId: string) => void
  onEditMessage?: (messageId: string) => void
  onRegenerateMessage?: (messageId: string) => void
  className?: string
}

export function MessageList({
  messages,
  onDeleteMessage,
  onEditMessage,
  onRegenerateMessage,
  className = "",
}: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center space-y-4 p-8 max-w-2xl">
          <div className="flex justify-center">
            <div className="relative">
              <MessageSquare className="h-12 w-12 text-muted-foreground/50" />
              <Sparkles className="h-5 w-5 text-primary absolute -top-1 -right-1" />
            </div>
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-medium">Start a conversation with Wendy</h3>
            <p className="text-sm text-muted-foreground">
              I&apos;m here to help you with trading psychology, mindset optimization, and performance improvement.
            </p>
          </div>
          <div className="grid gap-2 text-sm">
            <div className="px-4 py-2 rounded-lg border bg-muted/50 text-left">
              💭 &quot;How can I manage my emotions after a losing trade?&quot;
            </div>
            <div className="px-4 py-2 rounded-lg border bg-muted/50 text-left">
              📊 &quot;Analyze my recent trading patterns for me&quot;
            </div>
            <div className="px-4 py-2 rounded-lg border bg-muted/50 text-left">
              🎯 &quot;Help me create a pre-market routine&quot;
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <ScrollArea className={`h-full ${className}`}>
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="space-y-6">
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onDelete={onDeleteMessage ? () => onDeleteMessage(message.id) : undefined}
              onEdit={onEditMessage ? () => onEditMessage(message.id) : undefined}
              onRegenerate={onRegenerateMessage ? () => onRegenerateMessage(message.id) : undefined}
            />
          ))}
        </div>
      </div>
    </ScrollArea>
  )
}
