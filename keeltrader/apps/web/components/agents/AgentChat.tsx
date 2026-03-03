'use client'

import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { agentsAPI } from '@/lib/api/agents'
import type { AgentStatus } from '@/lib/types/agents'

interface AgentChatProps {
  agents: AgentStatus[]
  initialAgentId?: string
}

interface ChatMessage {
  role: 'user' | 'agent'
  agentId: string
  content: string
  timestamp: Date
  data?: Record<string, any>
}

export function AgentChat({ agents, initialAgentId }: AgentChatProps) {
  const [selectedAgent, setSelectedAgent] = useState(initialAgentId || agents[0]?.agent_id || '')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (initialAgentId) {
      setSelectedAgent(initialAgentId)
    }
  }, [initialAgentId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || !selectedAgent || sending) return

    const userMsg: ChatMessage = {
      role: 'user',
      agentId: selectedAgent,
      content: text,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)

    try {
      const resp = await agentsAPI.chatWithAgent({
        message: text,
        user_id: 'default',
        agent_id: selectedAgent,
      })
      const agentMsg: ChatMessage = {
        role: 'agent',
        agentId: resp.agent_id,
        content: resp.message,
        timestamp: new Date(),
        data: resp.data,
      }
      setMessages(prev => [...prev, agentMsg])
    } catch (e: any) {
      const errMsg: ChatMessage = {
        role: 'agent',
        agentId: selectedAgent,
        content: `Error: ${e.message || 'Failed to get response'}`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setSending(false)
    }
  }

  return (
    <Card className="flex h-[600px] flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-4">
          <CardTitle className="text-sm font-medium">Agent Chat</CardTitle>
          <Select value={selectedAgent} onValueChange={setSelectedAgent}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select agent" />
            </SelectTrigger>
            <SelectContent>
              {agents.map((a) => (
                <SelectItem key={a.agent_id} value={a.agent_id}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col overflow-hidden">
        {/* Messages */}
        <ScrollArea className="flex-1 pr-4" ref={scrollRef}>
          <div className="space-y-4 pb-4">
            {messages.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-8">
                Send a message to start chatting with an agent
              </p>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  {msg.role === 'agent' && (
                    <p className="mb-1 text-xs font-medium opacity-70">{msg.agentId}</p>
                  )}
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.data && Object.keys(msg.data).length > 0 && (
                    <pre className="mt-2 max-h-32 overflow-auto rounded bg-background/50 p-2 text-xs">
                      {JSON.stringify(msg.data, null, 2)}
                    </pre>
                  )}
                  <p className="mt-1 text-xs opacity-50">
                    {msg.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="rounded-lg bg-muted px-4 py-2 text-sm text-muted-foreground">
                  Thinking...
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="flex gap-2 pt-2 border-t">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Type a message..."
            disabled={sending}
          />
          <Button onClick={handleSend} disabled={sending || !input.trim()}>
            Send
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
