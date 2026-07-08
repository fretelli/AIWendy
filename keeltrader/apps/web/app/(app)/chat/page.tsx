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
import { apiStream, apiJson } from '@/lib/api/client';
import {
  getNumber,
  getString,
  isJsonObject,
  isOrderData,
  isPendingConfirmationResult,
  type JsonObject,
  type OrderData,
  type ToolCallData,
} from '@/components/v2/tool-call-types';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  toolCalls?: ToolCallData[];
  timestamp: Date;
}

const API_BASE = '/api/proxy/v1';

function parseStreamEvent(data: string): JsonObject | null {
  try {
    const parsed: unknown = JSON.parse(data);
    return isJsonObject(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

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
      const resp = await apiStream(`${API_BASE}/chat/send`, {
        method: 'POST',
        body: {
          message: text,
          session_id: sessionId,
        },
      });

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

          const event = parseStreamEvent(data);
          if (!event) continue;

            if (event.type === 'text') {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === 'assistant') {
                  last.content += getString(event.content);
                }
                return [...updated];
              });
            } else if (event.type === 'tool_call') {
              const name = getString(event.name);
              const args = isJsonObject(event.args) ? event.args : {};
              if (!name) continue;
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === 'assistant') {
                  last.toolCalls = [...(last.toolCalls || []), {
                    name,
                    args,
                  }];
                }
                return [...updated];
              });
            } else if (event.type === 'tool_result') {
              const name = getString(event.name);
              const result = isJsonObject(event.result) ? event.result : {};
              if (!name) continue;
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === 'assistant' && last.toolCalls) {
                  const tc = last.toolCalls.find(t => t.name === name && !t.result);
                  if (tc) tc.result = result;
                }
                return [...updated];
              });
            } else if (event.type === 'done') {
              const nextSessionId = getString(event.session_id);
              if (nextSessionId) setSessionId(nextSessionId);
            } else if (event.type === 'error') {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === 'assistant') {
                  last.content = `❌ ${getString(event.message, 'Request failed')}`;
                }
                return [...updated];
              });
            }
        }
      }
    } catch (error) {
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === 'assistant') {
          const message = error instanceof Error ? error.message : 'Unknown error';
          last.content = `❌ Connection error: ${message}`;
        }
        return [...updated];
      });
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId]);

  const handleQuickAction = useCallback(async (action: string, params?: JsonObject) => {
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
      const data = await apiJson<{ result: JsonObject }>(`${API_BASE}/chat/quick`, {
        method: 'POST',
        body: { action, params: params || {} },
      });

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
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ ${message}`,
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

  const handleConfirmOrder = useCallback(async (orderData: OrderData) => {
    const side = getString(orderData.side, 'order');
    const amount = getNumber(orderData.amount);
    const symbol = getString(orderData.symbol, 'unknown');
    await sendMessage(`Confirm execute: ${side} ${amount} ${symbol}`);
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
              <p className="text-lg">👋 Hi, I&apos;m KeelTrader AI Assistant</p>
              <p className="text-sm">Click the quick actions above or type your question</p>
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
                  {isPendingConfirmationResult(tc.result) && isOrderData(tc.result.order) ? (
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
                  Thinking...
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
            placeholder="Type a message... (Enter to send, Shift+Enter for new line)"
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
