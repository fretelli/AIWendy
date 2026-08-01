"use client";

import Link from "next/link";
import { ArrowUpRight, CircleStop, MessageSquarePlus, Send, Settings2 } from "lucide-react";
import { FormEvent } from "react";

import { DashboardPage, EmptyPanel, MetricCard, Panel, SectionTitle, StatusDot } from "@/components/agentos/dashboard-ui";
import { useAgentWorkspace } from "@/components/agentos/workspace-provider";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/lib/i18n/provider";

export default function AgentWorkspacePage() {
  const workspace = useAgentWorkspace();
  const { locale, formatNumber } = useI18n();
  const submit = (event: FormEvent) => { event.preventDefault(); void workspace.send(); };
  const toolEvents = workspace.events.filter((event) => event.type.startsWith("step.") || event.type.includes("tool") || event.type === "artifact.created");
  return <DashboardPage className="h-full min-h-0 overflow-hidden">
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4"><MetricCard label="SESSIONS" value={formatNumber(workspace.sessions.length)} note={locale === "zh" ? "用户拥有的研究会话" : "User-owned research sessions"} /><MetricCard label="RUN STATUS" value={workspace.activeRun?.status.toUpperCase() || "IDLE"} note={workspace.activeRun ? `${workspace.activeRun.current_step} steps · ${workspace.activeRun.tokens_used} tokens` : (locale === "zh" ? "没有运行中任务" : "No active run")} color={workspace.activeRun ? "text-agent-mint" : "text-agent-dim"} /><MetricCard label="VISIBLE EVENTS" value={formatNumber(workspace.events.length)} note={locale === "zh" ? "安全阶段、工具摘要与产物" : "Safe phases, tool summaries, artifacts"} color="text-agent-blue" /><MetricCard label="TOOL / ARTIFACT" value={formatNumber(toolEvents.length)} note={locale === "zh" ? "不展示模型思维链" : "No chain-of-thought shown"} color="text-agent-amber" /></div>
    <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-[280px_1fr]">
      <Panel className="min-h-0 overflow-hidden p-0"><div className="flex items-center border-b border-agent-border p-3"><SectionTitle title={locale === "zh" ? "会话" : "Sessions"} en="RESEARCH THREADS" action={<Button variant="ghost" size="icon" onClick={() => void workspace.newSession()}><MessageSquarePlus /></Button>} /></div><ScrollArea className="h-[calc(100%-56px)]"><div className="flex flex-col gap-1 p-2">{workspace.sessions.map((session) => <button key={session.id} type="button" onClick={() => workspace.setSessionId(session.id)} className={`rounded-md border px-3 py-3 text-left ${workspace.sessionId === session.id ? "border-agent-mint bg-agent-mint/5" : "border-transparent hover:bg-agent-raised"}`}><p className="truncate text-xs text-agent-text">{session.title}</p><div className="mt-2 flex items-center gap-2 font-data text-[8px] uppercase text-agent-dim"><StatusDot status={session.status} />{session.interaction_mode} · {session.workspace_scope}</div></button>)}{!workspace.sessions.length ? <EmptyPanel title={locale === "zh" ? "没有会话" : "No sessions"} detail={locale === "zh" ? "新建会话后开始研究。" : "Create a session to begin research."} /> : null}</div></ScrollArea></Panel>
      <Panel className="flex min-h-0 flex-col overflow-hidden p-0">
        <div className="flex items-center border-b border-agent-border px-4 py-3"><div><p className="text-sm text-agent-text">{workspace.sessions.find((item) => item.id === workspace.sessionId)?.title || (locale === "zh" ? "Agent 工作台" : "Agent Workspace")}</p><p className="mt-1 font-data text-[8px] uppercase text-agent-dim">ASK / RESEARCH / PLAN · SAFE TOOL TRACE</p></div><Link href="/agent/workspace/advanced" className="ml-auto inline-flex items-center gap-2 rounded border border-agent-border px-3 py-2 text-[10px] text-agent-muted hover:border-agent-mint hover:text-agent-mint"><Settings2 />{locale === "zh" ? "高级设置" : "Advanced"}<ArrowUpRight /></Link></div>
        <Tabs defaultValue="conversation" className="flex min-h-0 flex-1 flex-col"><TabsList className="mx-4 mt-3 h-auto w-fit border border-agent-border bg-agent-chrome p-1"><TabsTrigger value="conversation">{locale === "zh" ? "对话" : "Conversation"}</TabsTrigger><TabsTrigger value="queue">{locale === "zh" ? "任务队列" : "Task Queue"}</TabsTrigger><TabsTrigger value="trace">{locale === "zh" ? "运行轨迹" : "Trace"}</TabsTrigger><TabsTrigger value="tools">{locale === "zh" ? "工具日志" : "Tool Log"}</TabsTrigger></TabsList>
          <TabsContent value="conversation" className="mt-0 flex min-h-0 flex-1 flex-col"><ScrollArea className="min-h-0 flex-1"><div className="mx-auto flex max-w-3xl flex-col gap-4 p-4">{workspace.messages.map((message) => <article key={message.id} className={`max-w-[85%] rounded-md border px-4 py-3 text-xs leading-6 ${message.role === "user" ? "ml-auto border-agent-border-strong bg-agent-raised text-agent-text" : "border-transparent bg-agent-surface text-agent-muted"}`}><p className="mb-1 font-data text-[8px] uppercase text-agent-dim">{message.role}</p><p className="whitespace-pre-wrap">{message.content}</p></article>)}{workspace.events.filter((event) => event.type === "message.delta").length ? <article className="rounded-md bg-agent-surface px-4 py-3 text-xs leading-6 text-agent-muted">{workspace.events.filter((event) => event.type === "message.delta").map((event) => String(event.payload.delta || "")).join("")}<span className="ml-1 inline-block h-3 w-px animate-pulse bg-agent-mint" /></article> : null}</div></ScrollArea><form onSubmit={submit} className="border-t border-agent-border p-3"><div className="mx-auto flex max-w-3xl items-end gap-2 rounded-md border border-agent-border-strong bg-agent-surface p-2"><Textarea value={workspace.input} onChange={(event) => workspace.setInput(event.target.value)} placeholder={locale === "zh" ? "输入研究问题…" : "Enter a research question…"} className="min-h-12 resize-none border-0 bg-transparent focus-visible:ring-0" />{workspace.activeRun ? <Button type="button" variant="ghost" size="icon" onClick={() => void workspace.stop()}><CircleStop /></Button> : <Button type="submit" size="icon" disabled={!workspace.input.trim() || workspace.sending}><Send /></Button>}</div></form></TabsContent>
          <TabsContent value="queue" className="mt-0 min-h-0 flex-1 overflow-auto p-4"><RunList events={workspace.events.filter((event) => event.type.startsWith("run."))} locale={locale} /></TabsContent>
          <TabsContent value="trace" className="mt-0 min-h-0 flex-1 overflow-auto p-4"><RunList events={workspace.events} locale={locale} /></TabsContent>
          <TabsContent value="tools" className="mt-0 min-h-0 flex-1 overflow-auto p-4"><RunList events={toolEvents} locale={locale} /></TabsContent>
        </Tabs>
      </Panel>
    </div>
  </DashboardPage>;
}

function RunList({ events, locale }: { events: Array<{ id: string; type: string; payload: Record<string, unknown> }>; locale: string }) {
  return events.length ? <div className="mx-auto max-w-4xl divide-y divide-agent-border rounded-md border border-agent-border bg-agent-surface px-4">{events.map((event) => <div key={event.id} className="grid gap-3 py-3 md:grid-cols-[150px_1fr]"><span className="font-data text-[9px] uppercase text-agent-mint">{event.type}</span><pre className="overflow-auto whitespace-pre-wrap font-data text-[9px] leading-5 text-agent-muted">{JSON.stringify(event.payload, null, 2)}</pre></div>)}</div> : <EmptyPanel title={locale === "zh" ? "暂无事件" : "No events"} detail={locale === "zh" ? "运行开始后这里只展示安全阶段、工具摘要与产物，不展示思维链。" : "Once a run starts, only safe phases, tool summaries, and artifacts appear here—not chain-of-thought."} />;
}
