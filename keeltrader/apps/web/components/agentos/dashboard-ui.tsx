"use client";

import { AlertTriangle, ArrowUpRight, Database, Plus } from "lucide-react";
import { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function DashboardPage({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("mx-auto flex min-h-full w-full max-w-[1458px] flex-col gap-3 p-3 lg:p-4", className)}>{children}</div>;
}

export function Panel({ children, className, tone = "default" }: { children: ReactNode; className?: string; tone?: "default" | "raised" }) {
  return <section className={cn("rounded-md border border-agent-border p-4", tone === "raised" ? "bg-agent-raised" : "bg-agent-surface", className)}>{children}</section>;
}

export function SectionTitle({ title, action }: { title: string; en?: string; action?: ReactNode }) {
  return <div className="mb-3 flex min-h-7 items-center gap-2"><h2 className="text-sm font-medium text-agent-text">{title}</h2><div className="ml-auto">{action}</div></div>;
}

export function MetricCard({ label, value, note, color = "text-agent-text", progress }: { label: string; value: string; note?: string; color?: string; progress?: number }) {
  return <Panel className="min-h-[108px]">
    <p className="font-data text-[9px] uppercase tracking-[.08em] text-agent-dim">{label}</p>
    <p className={cn("mt-2 font-data text-[22px] leading-none", color)}>{value}</p>
    {progress !== undefined ? <div className="mt-4 h-1 overflow-hidden rounded bg-agent-border"><span className="block h-full bg-current" style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} /></div> : null}
    {note ? <p className="mt-3 text-[10px] leading-4 text-agent-dim">{note}</p> : null}
  </Panel>;
}

export function StatusDot({ status }: { status?: string }) {
  const color = status === "complete" || status === "active" || status === "confirmed" || status === "ready" ? "bg-agent-mint" : status === "partial" || status === "draft" ? "bg-agent-amber" : "bg-agent-dim";
  return <span className={cn("inline-block size-1.5 rounded-full", color)} />;
}

export function EmptyPanel({ title, detail, action, onAction }: { title: string; detail: string; action?: string; onAction?: () => void }) {
  return <div className="flex min-h-[160px] flex-col items-center justify-center rounded-md border border-dashed border-agent-border-strong px-6 text-center">
    <Database className="mb-3 text-agent-dim" />
    <p className="text-sm text-agent-muted">{title}</p>
    <p className="mt-1 max-w-md text-[10px] leading-4 text-agent-dim">{detail}</p>
    {action && onAction ? <Button variant="outline" size="sm" className="mt-4" onClick={onAction}><Plus />{action}</Button> : null}
  </div>;
}

export function MissingData({ items }: { items: Array<{ symbol?: string; currency?: string; kind?: string; reason: string }> }) {
  if (!items.length) return null;
  return <div className="flex items-start gap-2 rounded-md border border-agent-amber/30 bg-agent-amber/5 px-3 py-2 text-[10px] text-agent-amber"><AlertTriangle /><span>{items.map((item) => `${item.symbol || item.currency || item.kind || "data"}: ${item.reason}`).join(" · ")}</span></div>;
}

export function MiniLine({ values, color = "var(--agent-mint)", height = 72 }: { values: number[]; color?: string; height?: number }) {
  const safe = values.length > 1 ? values : [0, 0];
  const min = Math.min(...safe), max = Math.max(...safe), range = max - min || 1;
  const points = safe.map((value, index) => `${(index / (safe.length - 1)) * 100},${height - 6 - ((value - min) / range) * (height - 12)}`).join(" ");
  return <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className="h-full w-full" role="img" aria-label="trend"><defs><linearGradient id={`line-${color.replace(/\W/g, "")}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={color} stopOpacity=".24"/><stop offset="1" stopColor={color} stopOpacity="0"/></linearGradient></defs><polygon points={`0,${height} ${points} 100,${height}`} fill={`url(#line-${color.replace(/\W/g, "")})`} /><polyline points={points} fill="none" stroke={color} strokeWidth="1.4" vectorEffect="non-scaling-stroke" /></svg>;
}

export function Donut({ values, center, label }: { values: Array<{ value: number; color: string }>; center: string; label: string }) {
  const total = values.reduce((sum, item) => sum + item.value, 0) || 1;
  const segments = values.map((item, index) => ({
    ...item,
    length: item.value / total * 100,
    offset: values.slice(0, index).reduce((sum, previous) => sum + previous.value / total * 100, 0),
  }));
  return <div className="relative size-36"><svg viewBox="0 0 42 42" className="size-full -rotate-90" role="img" aria-label={label}>
    <circle cx="21" cy="21" r="15.915" fill="none" stroke="var(--agent-border)" strokeWidth="5" />
    {segments.map((item, index) => <circle key={index} cx="21" cy="21" r="15.915" fill="none" stroke={item.color} strokeWidth="5" strokeDasharray={`${item.length} ${100 - item.length}`} strokeDashoffset={-item.offset} />)}
  </svg><div className="absolute inset-0 flex flex-col items-center justify-center"><span className="font-data text-lg text-agent-text">{center}</span><span className="font-data text-[8px] uppercase tracking-[.08em] text-agent-dim">{label}</span></div></div>;
}

export function TextLink({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return <button type="button" onClick={onClick} className="inline-flex items-center gap-1 font-data text-[10px] text-agent-mint hover:text-agent-mint-bright">{children}<ArrowUpRight /></button>;
}
