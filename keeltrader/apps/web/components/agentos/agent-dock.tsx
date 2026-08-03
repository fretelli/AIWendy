"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  Bot,
  CircleStop,
  Loader2,
  MessageSquarePlus,
  Send,
  Sparkles,
} from "lucide-react";
import { FormEvent, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAgentWorkspace } from "@/components/agentos/workspace-provider";
import { useI18n } from "@/lib/i18n/provider";

export function AgentDock({ compact = false }: { compact?: boolean }) {
  const { locale } = useI18n();
  const workspace = useAgentWorkspace();
  const stream = useMemo(
    () =>
      workspace.events
        .filter((event) => event.type === "message.delta")
        .map((event) => String(event.payload.delta || ""))
        .join(""),
    [workspace.events],
  );
  const recent = workspace.messages.slice(-8);
  const lastHint = [...workspace.events]
    .reverse()
    .find((event) => event.navigation)?.navigation;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    void workspace.send();
  };
  return (
    <section
      className={`flex min-h-0 flex-col bg-agent-chrome ${compact ? "h-full" : "h-dvh border-l border-agent-border"}`}
    >
      <header className="flex h-[60px] shrink-0 items-center gap-3 border-b border-agent-border px-4">
        <span className="grid size-8 place-items-center rounded-md bg-agent-mint text-agent-canvas">
          <Bot />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-agent-text">
            {locale === "zh" ? "研究助手 Agent" : "Research Agent"}
          </p>
          <p className="font-data text-[10px] tracking-[.08em] text-agent-dim">
            {locale === "zh" ? "持续研究工作区" : "STREAMING WORKSPACE"}
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => void workspace.newSession()}
          title={locale === "zh" ? "新会话" : "New session"}
        >
          <MessageSquarePlus />
        </Button>
      </header>
      <ScrollArea className="min-h-0 flex-1">
        <div className="flex flex-col gap-4 p-4">
          {!recent.length && !stream ? (
            <div className="rounded-md border border-agent-border bg-agent-surface p-4">
              <Sparkles className="mb-3 text-agent-mint" />
              <p className="text-sm leading-6 text-agent-muted">
                {locale === "zh"
                  ? "问我关于组合、市场、宏观、机会或研究判断的问题。我会说明使用的数据，并给出可打开的对应模块。"
                  : "Ask about your portfolio, markets, macro, opportunities, or research. I will cite the data used and link the relevant module."}
              </p>
            </div>
          ) : null}
          {recent.map((message) => (
            <article
              key={message.id}
              className={`max-w-[92%] rounded-md border px-3 py-2.5 text-xs leading-5 ${message.role === "user" ? "ml-auto border-agent-border-strong bg-agent-raised text-agent-text" : "border-transparent bg-agent-surface text-agent-muted"}`}
            >
              <p className="mb-1 font-data text-[9px] tracking-[.12em] text-agent-dim">
                {message.role === "user"
                  ? locale === "zh"
                    ? "你"
                    : "YOU"
                  : locale === "zh"
                    ? "助手"
                    : "AGENT"}
              </p>
              <p className="whitespace-pre-wrap">{message.content}</p>
            </article>
          ))}
          {stream ? (
            <article className="rounded-md bg-agent-surface px-3 py-2.5 text-xs leading-5 text-agent-muted">
              <p className="mb-1 font-data text-[9px] tracking-[.12em] text-agent-mint">
                {locale === "zh" ? "助手 · 实时" : "AGENT · LIVE"}
              </p>
              <p className="whitespace-pre-wrap">
                {stream}
                <span className="ml-1 inline-block h-3 w-px animate-pulse bg-agent-mint" />
              </p>
            </article>
          ) : null}
          {lastHint ? (
            <button
              type="button"
              onClick={() => workspace.openHint(lastHint)}
              className="flex items-center justify-between rounded-md border border-agent-mint/40 bg-agent-mint/5 px-3 py-2 text-left text-xs text-agent-mint"
            >
              <span>
                {lastHint.label ||
                  (locale === "zh" ? "打开相关模块" : "Open related module")}
              </span>
              <ArrowUpRight />
            </button>
          ) : null}
        </div>
      </ScrollArea>
      <form
        onSubmit={submit}
        className="shrink-0 border-t border-agent-border p-3"
      >
        <div className="rounded-md border border-agent-border-strong bg-agent-surface p-2 focus-within:border-agent-mint/60">
          <textarea
            value={workspace.input}
            onChange={(event) => workspace.setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void workspace.send();
              }
            }}
            rows={compact ? 2 : 3}
            placeholder={locale === "zh" ? "问 Agent…" : "Ask Agent…"}
            className="w-full resize-none border-0 bg-transparent px-1 py-1 text-xs leading-5 text-agent-text outline-none placeholder:text-agent-dim focus:ring-0"
          />
          <div className="flex items-center justify-between pt-1">
            <span className="font-data text-[9px] text-agent-dim">
              {workspace.activeRun
                ? workspace.activeRun.status.toUpperCase()
                : locale === "zh"
                  ? "问答 · 研究"
                  : "ASK · RESEARCH"}
            </span>
            {workspace.activeRun ? (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={() => void workspace.stop()}
              >
                <CircleStop />
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                disabled={!workspace.input.trim() || workspace.sending}
              >
                {workspace.sending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Send />
                )}
              </Button>
            )}
          </div>
        </div>
        {!compact ? (
          <Link
            href="/agent/workspace"
            className="mt-2 flex items-center justify-center gap-1 py-1 font-data text-[9px] tracking-[.08em] text-agent-dim hover:text-agent-mint"
          >
            {locale === "zh" ? "完整 Agent 工作台" : "FULL AGENT WORKSPACE"}{" "}
            <ArrowUpRight />
          </Link>
        ) : null}
      </form>
    </section>
  );
}
