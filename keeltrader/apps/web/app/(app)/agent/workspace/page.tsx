"use client";

import {
  Download,
  MessageSquarePlus,
  MoreHorizontal,
  Pencil,
  Play,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  DashboardPage,
  EmptyPanel,
  Panel,
  SectionTitle,
  StatusDot,
} from "@/components/agentos/dashboard-ui";
import { useAgentWorkspace } from "@/components/agentos/workspace-provider";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  agentPlatformApi,
  type AgentRunTrace,
  type AgentSchedule,
} from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

export default function AgentWorkspacePage() {
  const workspace = useAgentWorkspace();
  const { locale } = useI18n();
  const [schedules, setSchedules] = useState<AgentSchedule[]>([]);
  const [trace, setTrace] = useState<AgentRunTrace | null>(null);
  const activeRunId = workspace.activeRun?.id;
  const activeTrace = trace?.run.id === activeRunId ? trace : null;
  const refreshSchedules = () =>
    agentPlatformApi.schedules().then((result) => setSchedules(result.items));

  useEffect(() => {
    void refreshSchedules().catch(() => undefined);
  }, []);
  useEffect(() => {
    if (!activeRunId) return;
    void agentPlatformApi
      .runTrace(activeRunId)
      .then(setTrace)
      .catch(() => undefined);
  }, [activeRunId, workspace.events.length]);

  return (
    <DashboardPage className="h-full min-h-0 overflow-hidden">
      <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-[.9fr_1.25fr_1fr]">
        <Panel className="min-h-0 overflow-hidden p-0">
          <div className="border-b border-agent-border p-4">
            <SectionTitle
              title={locale === "zh" ? "会话历史" : "SESSION HISTORY"}
              action={
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void workspace.newSession()}
                >
                  <MessageSquarePlus />
                  {locale === "zh" ? "新研究会话" : "NEW SESSION"}
                </Button>
              }
            />
          </div>
          <ScrollArea className="h-[calc(100%-68px)]">
            <div className="flex flex-col gap-2 p-3">
              {workspace.sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group rounded-md border p-3 ${workspace.sessionId === session.id ? "border-agent-mint bg-agent-mint/5" : "border-agent-border bg-agent-raised"}`}
                >
                  <div className="flex items-start gap-2">
                    <button
                      type="button"
                      onClick={() => workspace.setSessionId(session.id)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <div className="flex items-center gap-2">
                        <StatusDot status={session.status} />
                        <span className="font-data text-[9px] text-agent-dim">
                          {localizeMode(session.interaction_mode, locale)}
                        </span>
                        <span className="ml-auto font-data text-[9px] text-agent-dim">
                          {session.last_message_at.slice(0, 16)}
                        </span>
                      </div>
                      <p className="mt-3 truncate text-sm text-agent-text">
                        {session.title}
                      </p>
                      <p className="mt-2 line-clamp-2 text-[10px] leading-5 text-agent-muted">
                        {session.summary ||
                          (locale === "zh"
                            ? "尚无会话摘要"
                            : "No session summary yet")}
                      </p>
                    </button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={
                            locale === "zh" ? "会话操作" : "Session actions"
                          }
                        >
                          <MoreHorizontal />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => {
                            const title = window
                              .prompt(
                                locale === "zh"
                                  ? "重命名会话"
                                  : "Rename session",
                                session.title,
                              )
                              ?.trim();
                            if (title)
                              void workspace.renameSession(session.id, title);
                          }}
                        >
                          <Pencil />
                          {locale === "zh" ? "重命名" : "Rename"}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() =>
                            void workspace.exportSession(session.id)
                          }
                        >
                          <Download />
                          {locale === "zh" ? "导出" : "Export"}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          disabled={workspace.sessionId !== session.id}
                          onClick={() => void workspace.rerunLast()}
                        >
                          <Play />
                          {locale === "zh" ? "重跑" : "Rerun"}
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-agent-down"
                          onClick={() => {
                            if (
                              window.confirm(
                                locale === "zh"
                                  ? "确认删除这个会话？"
                                  : "Delete this session?",
                              )
                            )
                              void workspace.deleteSession(session.id);
                          }}
                        >
                          <Trash2 />
                          {locale === "zh" ? "删除" : "Delete"}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
              {!workspace.sessions.length ? (
                <EmptyPanel
                  title={locale === "zh" ? "没有会话" : "NO SESSIONS"}
                  detail={
                    locale === "zh"
                      ? "新建会话后开始研究。"
                      : "Create a session to begin research."
                  }
                />
              ) : null}
            </div>
          </ScrollArea>
        </Panel>

        <Panel className="min-h-0 overflow-hidden p-0">
          <div className="border-b border-agent-border p-4">
            <SectionTitle
              title={locale === "zh" ? "任务队列" : "JOB QUEUE"}
              action={
                <span className="font-data text-[9px] text-agent-mint">
                  {workspace.activeRun
                    ? locale === "zh"
                      ? "运行中"
                      : "RUNNING"
                    : locale === "zh"
                      ? "空闲"
                      : "IDLE"}
                </span>
              }
            />
          </div>
          <ScrollArea className="h-[calc(100%-68px)]">
            <div className="flex flex-col gap-3 p-4">
              {schedules.length ? (
                schedules.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-md border border-agent-border bg-agent-raised p-4"
                  >
                    <div className="flex items-center gap-2">
                      <StatusDot
                        status={item.enabled ? "active" : "unavailable"}
                      />
                      <p className="min-w-0 flex-1 truncate text-sm text-agent-text">
                        {item.name}
                      </p>
                      <button
                        type="button"
                        className="font-data text-[9px] text-agent-mint"
                        onClick={() =>
                          void agentPlatformApi
                            .updateSchedule(item.id, { enabled: !item.enabled })
                            .then(refreshSchedules)
                        }
                      >
                        {item.enabled
                          ? locale === "zh"
                            ? "暂停"
                            : "PAUSE"
                          : locale === "zh"
                            ? "启用"
                            : "ENABLE"}
                      </button>
                    </div>
                    <p className="mt-2 font-data text-[9px] text-agent-dim">
                      {item.cron} · {item.timezone}
                    </p>
                    <p className="mt-2 line-clamp-2 text-[10px] leading-5 text-agent-muted">
                      {item.prompt}
                    </p>
                    <div className="mt-3 flex gap-3">
                      <button
                        type="button"
                        className="text-[10px] text-agent-blue"
                        onClick={() => {
                          const name = window
                            .prompt(
                              locale === "zh" ? "任务名称" : "Job name",
                              item.name,
                            )
                            ?.trim();
                          if (name)
                            void agentPlatformApi
                              .updateSchedule(item.id, { name })
                              .then(refreshSchedules);
                        }}
                      >
                        {locale === "zh" ? "编辑触发条件" : "EDIT TRIGGER"}
                      </button>
                      <button
                        type="button"
                        className="text-[10px] text-agent-down"
                        onClick={() => {
                          if (
                            window.confirm(
                              locale === "zh"
                                ? "删除这个触发任务？"
                                : "Delete this trigger?",
                            )
                          )
                            void agentPlatformApi
                              .deleteSchedule(item.id)
                              .then(refreshSchedules);
                        }}
                      >
                        {locale === "zh" ? "删除" : "DELETE"}
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyPanel
                  title={locale === "zh" ? "没有定时任务" : "NO SCHEDULED JOBS"}
                  detail={
                    locale === "zh"
                      ? "任务触发条件将显示在这里。"
                      : "Job triggers appear here."
                  }
                />
              )}
              <div className="rounded-md border border-agent-border bg-agent-raised p-4">
                <SectionTitle
                  title={locale === "zh" ? "执行轨迹" : "EXECUTION TRACE"}
                />
                {workspace.events.length ? (
                  <SafeTrace events={workspace.events} locale={locale} />
                ) : (
                  <p className="text-[10px] leading-5 text-agent-dim">
                    {locale === "zh"
                      ? "只展示安全阶段、工具摘要与产物，不展示思维链。"
                      : "Only safe phases, tool summaries, and artifacts are shown."}
                  </p>
                )}
              </div>
            </div>
          </ScrollArea>
        </Panel>

        <Panel className="min-h-0 overflow-hidden p-0">
          <div className="border-b border-agent-border p-4">
            <SectionTitle
              title={
                locale === "zh"
                  ? "Tushare 数据调用日志"
                  : "TUSHARE DATA CALL LOG"
              }
              action={
                <span className="font-data text-[9px] text-agent-dim">
                  {activeTrace?.tushare_calls.length || 0}{" "}
                  {locale === "zh" ? "次" : "CALLS"}
                </span>
              }
            />
          </div>
          <ScrollArea className="h-[calc(100%-68px)]">
            <div className="divide-y divide-agent-border px-4">
              {activeTrace?.tushare_calls.length ? (
                activeTrace.tushare_calls.map((item) => (
                  <div
                    key={`${item.step_id}-${item.sequence}`}
                    className="py-4"
                  >
                    <div className="flex items-center gap-2">
                      <StatusDot status={item.status} />
                      <span className="font-data text-[10px] text-agent-mint">
                        {item.dataset ||
                          item.capability ||
                          (locale === "zh" ? "数据集" : "dataset")}
                      </span>
                      <span className="ml-auto font-data text-[9px] text-agent-dim">
                        #{item.sequence}
                      </span>
                    </div>
                    <p className="mt-2 font-data text-[9px] leading-5 text-agent-muted">
                      {locale === "zh" ? "字段" : "fields"}:{" "}
                      {item.requested_fields.join(", ") || "—"}
                      <br />
                      {locale === "zh" ? "过滤键" : "filters"}:{" "}
                      {item.filter_keys.join(", ") || "—"}
                    </p>
                    {item.error ? (
                      <p className="mt-2 text-[10px] text-agent-down">
                        {item.error}
                      </p>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="py-4">
                  <EmptyPanel
                    title={
                      locale === "zh" ? "暂无 Tushare 调用" : "NO TUSHARE CALLS"
                    }
                    detail={
                      locale === "zh"
                        ? "这里只展示数据集、字段、过滤键与结果摘要。"
                        : "Only datasets, fields, filters, and result summaries are shown."
                    }
                  />
                </div>
              )}
            </div>
          </ScrollArea>
        </Panel>
      </div>
    </DashboardPage>
  );
}

function localizeMode(value: string, locale: string) {
  if (locale !== "zh") return value.toUpperCase();
  return (
    ({ ask: "问答", research: "研究", plan: "规划" } as Record<string, string>)[
      value
    ] || value
  );
}

function SafeTrace({
  events,
  locale,
}: {
  events: Array<{ id: string; type: string; payload: Record<string, unknown> }>;
  locale: string;
}) {
  const hidden = new Set([
    "thought",
    "reasoning",
    "chain_of_thought",
    "chainOfThought",
    "prompt",
    "system_prompt",
  ]);
  const sanitize = (value: unknown): unknown =>
    Array.isArray(value)
      ? value.map(sanitize)
      : value && typeof value === "object"
        ? Object.fromEntries(
            Object.entries(value as Record<string, unknown>)
              .filter(
                ([key]) =>
                  !hidden.has(key) &&
                  !key.toLowerCase().includes("reasoning") &&
                  !key.toLowerCase().includes("thought"),
              )
              .map(([key, item]) => [key, sanitize(item)]),
          )
        : value;
  return (
    <div className="divide-y divide-agent-border">
      {events
        .slice(-12)
        .reverse()
        .map((event) => (
          <div key={event.id} className="py-3">
            <p className="font-data text-[9px] text-agent-mint">{event.type}</p>
            <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap font-data text-[9px] leading-5 text-agent-muted">
              {JSON.stringify(sanitize(event.payload), null, 2)}
            </pre>
          </div>
        ))}
      <p className="pt-3 text-[9px] text-agent-dim">
        {locale === "zh"
          ? "已自动移除提示词、推理与思维链字段。"
          : "Prompt, reasoning, and chain-of-thought fields are automatically removed."}
      </p>
    </div>
  );
}
