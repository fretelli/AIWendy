"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import {
  agentPlatformApi,
  type AgentDefinition,
  type AgentMessage,
  type AgentRun,
  type AgentSession,
} from "@/lib/api/agent-platform";

type NavigationHint = { route?: string; tab?: string; entity_id?: string; label?: string };
type DockEvent = { id: string; type: string; payload: Record<string, unknown>; navigation?: NavigationHint };

type AgentWorkspaceValue = {
  loading: boolean;
  sending: boolean;
  sessions: AgentSession[];
  sessionId: string | null;
  messages: AgentMessage[];
  events: DockEvent[];
  activeRun?: AgentRun;
  input: string;
  setInput: (value: string) => void;
  setSessionId: (value: string) => void;
  newSession: () => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  exportSession: (id: string) => Promise<void>;
  rerunLast: () => Promise<void>;
  send: (content?: string) => Promise<void>;
  stop: () => Promise<void>;
  openHint: (hint: NavigationHint) => void;
};

const AgentWorkspaceContext = createContext<AgentWorkspaceValue | null>(null);
const TERMINAL = new Set(["completed", "failed", "cancelled"]);
const ROUTE_ALLOWLIST = new Set([
  "/agent", "/agent/allocation", "/agent/holdings", "/agent/market",
  "/agent/opportunities", "/agent/decisions", "/agent/research", "/agent/workspace",
]);

export function AgentWorkspaceProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [sessionId, setSessionIdState] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [events, setEvents] = useState<DockEvent[]>([]);
  const [input, setInput] = useState("");
  const sourceRef = useRef<EventSource | null>(null);

  const refresh = useCallback(async () => {
    const [sessionData, agentData] = await Promise.all([
      agentPlatformApi.sessions(),
      agentPlatformApi.agents(),
    ]);
    setSessions(sessionData.items);
    setAgents(agentData.items);
    setSessionIdState((current) => current || sessionData.items[0]?.id || null);
  }, []);

  const loadTimeline = useCallback(async (id: string) => {
    const timeline = await agentPlatformApi.timeline(id);
    setMessages(timeline.messages);
    setRuns(timeline.runs);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [sessionData, agentData] = await Promise.all([
        agentPlatformApi.sessions(),
        agentPlatformApi.agents(),
      ]);
      if (cancelled) return;
      setSessions(sessionData.items);
      setAgents(agentData.items);
      setSessionIdState((current) => current || sessionData.items[0]?.id || null);
      setLoading(false);
    })().catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    void (async () => {
      const timeline = await agentPlatformApi.timeline(sessionId);
      if (cancelled) return;
      setMessages(timeline.messages);
      setRuns(timeline.runs);
    })().catch(() => undefined);
    return () => { cancelled = true; };
  }, [sessionId]);

  const activeRun = useMemo(() => [...runs].reverse().find((run) => !TERMINAL.has(run.status)), [runs]);

  useEffect(() => {
    sourceRef.current?.close();
    if (!activeRun) return;
    const source = new EventSource(`/api/proxy/v1/agent/runs/${activeRun.id}/events`);
    sourceRef.current = source;
    const receive = (event: MessageEvent) => {
      let payload: Record<string, unknown> = {};
      try { payload = JSON.parse(event.data) as Record<string, unknown>; }
      catch { payload = { text: event.data }; }
      const rawHint = payload.ui_hint ?? payload.navigation_hint;
      const navigation = rawHint && typeof rawHint === "object" ? rawHint as NavigationHint : undefined;
      setEvents((current) => [...current, {
        id: event.lastEventId || crypto.randomUUID(),
        type: event.type,
        payload,
        navigation,
      }].slice(-120));
      if (["run.completed", "run.failed", "run.cancel"].includes(event.type)) {
        source.close();
        if (sessionId) void loadTimeline(sessionId);
        void refresh();
      }
    };
    for (const type of ["run.queued", "run.planned", "message.delta", "step.started", "step.completed", "approval.required", "artifact.created", "navigation.hint", "run.completed", "run.failed", "run.cancel"]) {
      source.addEventListener(type, receive);
    }
    source.onerror = () => source.close();
    return () => source.close();
  }, [activeRun, loadTimeline, refresh, sessionId]);

  const createSession = useCallback(async () => {
    const definition = agents[0];
    if (!definition) {
      router.push("/agent/workspace");
      return null;
    }
    const created = await agentPlatformApi.createSession({
      agent_definition_id: definition.id,
      title: "AgentOS 研究会话",
      interaction_mode: "ask",
      workspace_scope: "research",
    });
    setSessions((current) => [created, ...current]);
    setSessionIdState(created.id);
    setMessages([]);
    setRuns([]);
    setEvents([]);
    return created.id;
  }, [agents, router]);

  const send = useCallback(async (content?: string) => {
    const prompt = (content ?? input).trim();
    if (!prompt || sending) return;
    setSending(true);
    if (!content) setInput("");
    try {
      let target = sessionId;
      if (!target) target = await createSession();
      if (!target) return;
      const context = `\n\n[AgentOS UI context: ${pathname}]`;
      const result = await agentPlatformApi.sendMessage(target, {
        content: `${prompt}${context}`,
        client_request_id: crypto.randomUUID(),
        agent_definition_id: agents[0]?.id,
      });
      setRuns((current) => [...current, result.run]);
      setEvents([]);
      await loadTimeline(target);
    } finally {
      setSending(false);
    }
  }, [agents, createSession, input, loadTimeline, pathname, sending, sessionId]);

  const stop = useCallback(async () => {
    if (!sessionId) return;
    await agentPlatformApi.stopSession(sessionId);
    await loadTimeline(sessionId);
  }, [loadTimeline, sessionId]);

  const renameSession = useCallback(async (id: string, title: string) => {
    const value = title.trim();
    if (!value) return;
    const updated = await agentPlatformApi.updateSession(id, { title: value });
    setSessions((current) => current.map((item) => item.id === id ? updated : item));
  }, []);

  const deleteSession = useCallback(async (id: string) => {
    await agentPlatformApi.deleteSession(id);
    const remaining = sessions.filter((item) => item.id !== id);
    setSessions(remaining);
    if (sessionId === id) setSessionIdState(remaining[0]?.id || null);
  }, [sessionId, sessions]);

  const exportSession = useCallback(async (id: string) => {
    const timeline = await agentPlatformApi.timeline(id);
    const url = URL.createObjectURL(new Blob([JSON.stringify(timeline, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `keeltrader-session-${id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, []);

  const rerunLast = useCallback(async () => {
    const last = [...messages].reverse().find((message) => message.role === "user");
    if (last) await send(last.content);
  }, [messages, send]);

  const openHint = useCallback((hint: NavigationHint) => {
    if (!hint.route || !ROUTE_ALLOWLIST.has(hint.route)) return;
    const params = new URLSearchParams();
    if (hint.tab) params.set("tab", hint.tab);
    if (hint.entity_id) params.set("entity", hint.entity_id);
    router.push(`${hint.route}${params.size ? `?${params}` : ""}`);
  }, [router]);

  const value = useMemo<AgentWorkspaceValue>(() => ({
    loading, sending, sessions, sessionId, messages, events, activeRun, input, setInput,
    setSessionId: setSessionIdState, newSession: async () => { await createSession(); }, renameSession, deleteSession,
    exportSession, rerunLast, send, stop, openHint,
  }), [activeRun, createSession, deleteSession, events, exportSession, input, loading, messages, openHint, renameSession, rerunLast, send, sending, sessionId, sessions, stop]);

  return <AgentWorkspaceContext.Provider value={value}>{children}</AgentWorkspaceContext.Provider>;
}

export function useAgentWorkspace() {
  const value = useContext(AgentWorkspaceContext);
  if (!value) throw new Error("useAgentWorkspace must be used inside AgentWorkspaceProvider");
  return value;
}
