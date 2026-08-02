"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Bot, FileDown, Menu } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AgentDock } from "@/components/agentos/agent-dock";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { agentOSApi, type AgentOSOverview, type PortfolioAnalytics } from "@/lib/api/agentos";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

type ModuleItem = {
  no: string;
  href: string;
  zh: string;
  en: string;
  zhTitle: string;
  enTitle: string;
  tabs?: Array<{ value: string; zh: string; en: string }>;
};

const modules: ModuleItem[] = [
  { no: "01", href: "/agent", zh: "总览", en: "Overview", zhTitle: "总览", enTitle: "OVERVIEW" },
  { no: "02", href: "/agent/allocation", zh: "配置", en: "Allocation", zhTitle: "资产配置", enTitle: "ASSET ALLOCATION", tabs: [
    { value: "saa", zh: "SAA", en: "SAA" }, { value: "taa", zh: "TAA", en: "TAA" },
    { value: "rebalance", zh: "再平衡", en: "Rebalance" }, { value: "stress", zh: "压力测试", en: "Stress" },
  ] },
  { no: "03", href: "/agent/holdings", zh: "持仓", en: "Holdings", zhTitle: "我的持仓", enTitle: "HOLDINGS", tabs: [
    { value: "detail", zh: "持仓明细", en: "Positions" }, { value: "hedge", zh: "对冲与衍生品", en: "Hedge & Derivatives" },
  ] },
  { no: "04", href: "/agent/market", zh: "市场", en: "Market", zhTitle: "市场与宏观", enTitle: "MARKET & MACRO", tabs: [
    { value: "market", zh: "大盘 · 行业 · 资金流", en: "Market · Sectors · Flows" },
    { value: "macro", zh: "宏观数据", en: "Macro Data" },
  ] },
  { no: "05", href: "/agent/opportunities", zh: "机会", en: "Opportunities", zhTitle: "机会 · 信号 / 价差", enTitle: "OPPORTUNITIES", tabs: [
    { value: "signals", zh: "信号流", en: "Signal Feed" }, { value: "relative", zh: "相对价值与套利", en: "Relative Value" },
  ] },
  { no: "06", href: "/agent/decisions", zh: "决策", en: "Decisions", zhTitle: "决策 · 条件 / 归因 / 策略", enTitle: "DECISIONS", tabs: [
    { value: "conditions", zh: "条件与时机", en: "Conditions" }, { value: "log", zh: "决策日志", en: "Decision Log" },
    { value: "attribution", zh: "收益归因", en: "Attribution" }, { value: "strategy", zh: "策略实验室", en: "Strategy Lab" },
  ] },
  { no: "07", href: "/agent/research", zh: "研报", en: "Research", zhTitle: "假设检验 · 判断记录 / 研报", enTitle: "RESEARCH", tabs: [
    { value: "thesis", zh: "假设检验", en: "Hypothesis Tests" }, { value: "record", zh: "我的判断记录", en: "Judgment Record" },
    { value: "consensus", zh: "共识与分歧", en: "Consensus" }, { value: "library", zh: "全部研报", en: "All Reports" },
  ] },
  { no: "08", href: "/agent/workspace", zh: "Agent", en: "Agent", zhTitle: "Agent 工作台 · 会话与任务", enTitle: "AGENT WORKSPACE" },
];

const tabDefaults: Record<string, string> = {
  "/agent/allocation": "saa", "/agent/holdings": "detail", "/agent/market": "market",
  "/agent/opportunities": "signals", "/agent/decisions": "conditions", "/agent/research": "thesis",
};

function activeModule(pathname: string) {
  return modules.find((item) => item.href === "/agent" ? pathname === "/agent" : pathname.startsWith(item.href)) ?? modules[0];
}

function ModuleNavigation({ mobile = false, close, period }: { mobile?: boolean; close?: () => void; period: string }) {
  const pathname = usePathname();
  const { locale } = useI18n();
  return <nav className={mobile ? "flex flex-col gap-1" : "flex w-full flex-col items-center gap-1"} aria-label={locale === "zh" ? "AgentOS 模块" : "AgentOS modules"}>
    {modules.map((item) => {
      const active = item.href === "/agent" ? pathname === item.href : pathname.startsWith(item.href);
      return <Link key={item.href} href={`${item.href}?period=${period}`} onClick={close} className={cn(
        mobile ? "h-12 flex-row justify-start px-3" : "h-[58px] w-[62px] flex-col justify-center",
        "flex items-center gap-1 rounded-md border-l-2 transition-colors",
        active ? "border-agent-mint bg-agent-raised text-agent-text" : "border-transparent text-agent-dim hover:bg-agent-surface hover:text-agent-muted",
      )}>
        <span className="font-data text-xs font-medium">{item.no}</span>
        <span className="text-[10px]">{locale === "zh" ? item.zh : item.en}</span>
      </Link>;
    })}
  </nav>;
}

function HeaderTabs({ current, period }: { current: ModuleItem; period: string }) {
  const params = useSearchParams();
  const { locale } = useI18n();
  if (!current.tabs?.length) return null;
  const requested = params.get("tab") || tabDefaults[current.href];
  const aliases: Record<string, string> = current.href === "/agent/opportunities" ? { people: "signals" }
    : current.href === "/agent/research" ? { hypotheses: "thesis", judgments: "record", reports: "library" }
      : {};
  const active = aliases[requested] || requested;
  return <nav className="hidden min-w-0 flex-1 items-center gap-1 overflow-x-auto lg:flex" aria-label={locale === "zh" ? "模块视图" : "Module views"}>
    {current.tabs.map((tab) => {
      const query = new URLSearchParams();
      query.set("period", period);
      query.set("tab", tab.value);
      if (current.href === "/agent/market") query.set("view", tab.value === "macro" ? "dashboard" : "overview");
      return <Link key={tab.value} href={`${current.href}?${query}`} className={cn(
        "shrink-0 rounded-md border px-3 py-1.5 text-[11px] transition-colors",
        active === tab.value ? "border-agent-mint bg-agent-mint/10 text-agent-mint" : "border-agent-border text-agent-muted hover:border-agent-border-strong hover:text-agent-text",
      )}>{locale === "zh" ? tab.zh : tab.en}</Link>;
    })}
  </nav>;
}

export function AgentOsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { locale, setLocale, formatCurrency } = useI18n();
  const [overview, setOverview] = useState<AgentOSOverview | null>(null);
  const [shellError, setShellError] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);
  const current = useMemo(() => activeModule(pathname), [pathname]);
  const period = ["1M", "3M", "1Y", "3Y"].includes(searchParams.get("period") || "") ? searchParams.get("period")! : "1Y";
  const setPeriod = (next: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("period", next);
    router.replace(`${pathname}?${params.toString()}`);
  };
  useEffect(() => {
    let cancelled = false;
    void agentOSApi.overview().then((value) => {
      if (!cancelled) { setOverview(value); setShellError(false); }
    }).catch(() => { if (!cancelled) setShellError(true); });
    return () => { cancelled = true; };
  }, [pathname]);
  const portfolio = overview?.portfolio && "total_value" in overview.portfolio ? overview.portfolio : null;
  const analytics = overview?.analytics && "total_value" in overview.analytics ? overview.analytics as PortfolioAnalytics : null;
  const today = analytics?.today_pnl.value ?? undefined;
  const cash = analytics?.cash.value ?? undefined;
  return <div className="flex h-dvh min-h-0 overflow-hidden bg-agent-canvas text-agent-text">
    <aside className="hidden w-[78px] shrink-0 flex-col items-center border-r border-agent-border bg-agent-chrome px-0 py-[18px] lg:flex">
      <Link href="/agent" className="mb-[22px] grid size-[34px] place-items-center rounded-lg bg-agent-mint font-data text-[15px] font-semibold text-agent-canvas">A</Link>
      <ModuleNavigation period={period} />
      <div className="mt-auto flex flex-col items-center gap-2"><span className="size-2 rounded-full bg-agent-mint shadow-[0_0_12px_var(--agent-mint)]" /><span className="font-data text-[9px] [writing-mode:vertical-rl] text-agent-dim">{overview ? `${overview.tasks.active} ACTIVE · ${overview.tasks.total} JOBS` : "AGENT STATUS"}</span></div>
    </aside>
    <section className="flex min-w-0 flex-1 flex-col">
      <header className="flex h-[60px] shrink-0 items-center gap-3 border-b border-agent-border bg-agent-chrome px-4 lg:px-[26px]">
        <Sheet open={navOpen} onOpenChange={setNavOpen}>
          <SheetTrigger asChild><Button variant="ghost" size="icon" className="lg:hidden"><Menu /></Button></SheetTrigger>
          <SheetContent side="left" className="w-[280px] border-agent-border bg-agent-chrome text-agent-text"><SheetHeader><SheetTitle className="text-left text-agent-text">KeelTrader AgentOS</SheetTitle><SheetDescription className="sr-only">{locale === "zh" ? "选择 AgentOS 一级模块" : "Choose an AgentOS module"}</SheetDescription></SheetHeader><div className="mt-6"><ModuleNavigation mobile period={period} close={() => setNavOpen(false)} /></div></SheetContent>
        </Sheet>
        <div className="flex shrink-0 items-baseline gap-2">
          <h1 className="whitespace-nowrap text-[17px] font-medium">{locale === "zh" ? current.zhTitle : current.en}</h1>
          <span className="hidden font-data text-[9px] uppercase tracking-[.08em] text-agent-dim xl:inline">{current.enTitle}</span>
        </div>
        <HeaderTabs current={current} period={period} />
        <div className="hidden shrink-0 overflow-hidden rounded-md border border-agent-border md:flex">
          {["1M", "3M", "1Y", "3Y"].map((value) => <button type="button" key={value} onClick={() => setPeriod(value)} aria-pressed={period === value} className={cn("px-2.5 py-1.5 font-data text-[10px]", period === value ? "bg-agent-mint text-agent-canvas" : "text-agent-dim hover:text-agent-text")}>{value}</button>)}
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <div className="hidden items-center gap-2 font-data text-[9px] text-agent-muted xl:flex"><span className={cn("size-1.5 rounded-full", shellError ? "bg-agent-up" : overview?.data_status === "complete" ? "bg-agent-mint" : "bg-agent-amber")} />{shellError ? "API ERROR" : `${overview?.as_of || "—"} · DATA`}</div>
          <Button onClick={() => router.push(`/agent/research?period=${period}&tab=library&report=1`)} className="hidden bg-agent-mint text-agent-canvas hover:bg-agent-mint-bright 2xl:inline-flex"><FileDown />{locale === "zh" ? "生成报告" : "Export"}</Button>
          <button type="button" onClick={() => setLocale(locale === "zh" ? "en" : "zh")} className="rounded border border-agent-border px-2 py-1 font-data text-[10px] text-agent-muted hover:border-agent-mint hover:text-agent-mint">{locale === "zh" ? "EN" : "中"}</button>
          <div className="hidden gap-3 border-l border-agent-border pl-3 2xl:flex">
            <Metric label="TOTAL MV" value={portfolio ? formatCurrency(portfolio.total_value, portfolio.base_currency) : "—"} />
            <Metric label="TODAY" value={today !== undefined ? formatCurrency(today, analytics?.base_currency) : "—"} accent={today !== undefined && today >= 0} />
            <Metric label="CASH" value={cash !== undefined ? formatCurrency(cash, analytics?.base_currency) : "—"} />
          </div>
          <Button variant="ghost" size="icon" className="2xl:hidden" onClick={() => setAgentOpen(true)}><Bot /></Button>
        </div>
      </header>
      <main className="min-h-0 flex-1 overflow-y-auto bg-agent-canvas">{children}</main>
    </section>
    <aside className="hidden w-[384px] shrink-0 2xl:block"><AgentDock /></aside>
    <Sheet open={agentOpen} onOpenChange={setAgentOpen}>
      <SheetContent side="right" className="w-full border-agent-border bg-agent-chrome p-0 text-agent-text sm:max-w-[420px]"><SheetHeader className="sr-only"><SheetTitle>Agent</SheetTitle><SheetDescription>{locale === "zh" ? "持续研究对话与安全工具摘要" : "Persistent research chat and safe tool summaries"}</SheetDescription></SheetHeader><AgentDock compact /></SheetContent>
    </Sheet>
  </div>;
}

function Metric({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return <div className="flex min-w-[76px] flex-col gap-0.5"><span className="font-data text-[8px] tracking-[.08em] text-agent-dim">{label}</span><span className={cn("max-w-[110px] truncate font-data text-[11px]", accent ? "text-agent-mint" : "text-agent-text")}>{value}</span></div>;
}
