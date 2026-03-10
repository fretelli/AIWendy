'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { Send, Loader2 } from 'lucide-react';
import { QuickActions } from '@/components/v2/QuickActions';
import { ToolCallCard } from '@/components/v2/ToolCallCard';
import { OrderConfirmCard } from '@/components/v2/OrderConfirmCard';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  toolCalls?: ToolCallData[];
  timestamp: Date;
}

interface ToolCallData {
  name: string;
  args: Record<string, any>;
  result?: Record<string, any>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('keeltrader_access_token') || localStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      toolCalls: [],
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      const resp = await fetch(`${API_BASE}/api/v1/chat/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
        }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (!data) continue;

          try {
            const event = JSON.parse(data);

            if (event.type === 'text') {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === 'assistant') {
                  last.content += event.content;
                }
                return [...updated];
              });
            } else if (event.type === 'tool_call') {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === 'assistant') {
                  last.toolCalls = [...(last.toolCalls || []), {
                    name: event.name,
                    args: event.args,
                  }];
                }
                return [...updated];
              });
            } else if (event.type === 'tool_result') {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === 'assistant' && last.toolCalls) {
                  const tc = last.toolCalls.find(t => t.name === event.name && !t.result);
                  if (tc) tc.result = event.result;
                }
                return [...updated];
              });
            } else if (event.type === 'done') {
              if (event.session_id) setSessionId(event.session_id);
            } else if (event.type === 'error') {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === 'assistant') {
                  last.content = `❌ ${event.message}`;
                }
                return [...updated];
              });
            }
          } catch (e) {
            // Skip unparseable events
          }
        }
      }
    } catch (e: any) {
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === 'assistant') {
          last.content = `❌ 连接错误: ${e.message}`;
        }
        return [...updated];
      });
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId]);

  const handleQuickAction = useCallback(async (action: string, params?: Record<string, any>) => {
    if (isLoading) return;
    setIsLoading(true);

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: `[${action}]`,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      const resp = await fetch(`${API_BASE}/api/v1/chat/quick`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ action, params: params || {} }),
      });

      const data = await resp.json();

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        toolCalls: [{
          name: action,
          args: params || {},
          result: data.result,
        }],
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e: any) {
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ ${e.message}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleConfirmOrder = useCallback(async (orderData: Record<string, any>) => {
    await sendMessage(`确认执行: ${orderData.side} ${orderData.amount} ${orderData.symbol}`);
  }, [sendMessage]);

  return (
    <div className="flex flex-col h-full">
      {/* Quick actions bar */}
      <QuickActions onAction={handleQuickAction} disabled={isLoading} />

      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center space-y-2">
              <p className="text-lg">👋 你好，我是 KeelTrader AI 助手</p>
              <p className="text-sm">点击上方快捷按钮或直接输入你的问题</p>
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div
            key={msg.id}
            className={cn(
              'flex',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                'max-w-[85%] rounded-lg px-4 py-2',
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted'
              )}
            >
              {/* Tool calls */}
              {msg.toolCalls?.map((tc, i) => (
                <div key={i} className="mb-2">
                  {tc.result?.status === 'pending_confirmation' ? (
                    <OrderConfirmCard
                      order={tc.result.order}
                      message={tc.result.message}
                      onConfirm={handleConfirmOrder}
                    />
                  ) : (
                    <ToolCallCard
                      name={tc.name}
                      args={tc.args}
                      result={tc.result}
                    />
                  )}
                </div>
              ))}

              {/* Text content */}
              {msg.content && (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}

              {/* Loading indicator for streaming */}
              {msg.role === 'assistant' && !msg.content && !msg.toolCalls?.length && isLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  思考中...
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input area */}
      <div className="border-t p-4">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
            className="flex-1 resize-none rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary min-h-[40px] max-h-[120px]"
            rows={1}
            disabled={isLoading}
          />
          <Button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isLoading}
            size="icon"
            className="shrink-0"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
