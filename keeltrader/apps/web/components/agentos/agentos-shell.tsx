"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bot, FileDown, Menu } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AgentDock } from "@/components/agentos/agent-dock";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { agentOSApi, type AgentOSOverview } from "@/lib/api/agentos";
import { useI18n } from "@/lib/i18n/provider";

const modules = [
  { no: "01", href: "/agent", zh: "总览", en: "Overview" },
  { no: "02", href: "/agent/allocation", zh: "配置", en: "Allocation" },
  { no: "03", href: "/agent/holdings", zh: "持仓", en: "Holdings" },
  { no: "04", href: "/agent/market", zh: "市场", en: "Market" },
  { no: "05", href: "/agent/opportunities", zh: "机会", en: "Opportunities" },
  { no: "06", href: "/agent/decisions", zh: "决策", en: "Decisions" },
  { no: "07", href: "/agent/research", zh: "研究", en: "Research" },
  { no: "08", href: "/agent/workspace", zh: "Agent", en: "Agent" },
] as const;

function activeModule(pathname: string) {
  return modules.find((item) => item.href === "/agent" ? pathname === "/agent" : pathname.startsWith(item.href)) ?? modules[0];
}

function ModuleNavigation({ mobile = false, close }: { mobile?: boolean; close?: () => void }) {
  const pathname = usePathname();
  const { locale } = useI18n();
  return (
    <nav className={mobile ? "flex flex-col gap-1" : "flex w-full flex-col items-center gap-1"} aria-label={locale === "zh" ? "AgentOS 模块" : "AgentOS modules"}>
      {modules.map((item) => {
        const active = item.href === "/agent" ? pathname === item.href : pathname.startsWith(item.href);
        return <Link key={item.href} href={item.href} onClick={close} className={`${mobile ? "h-12 flex-row justify-start px-3" : "h-[58px] w-[62px] flex-col justify-center"} flex items-center gap-1 rounded-md border-l-2 transition-colors ${active ? "border-agent-mint bg-agent-raised text-agent-text" : "border-transparent text-agent-dim hover:bg-agent-surface hover:text-agent-muted"}`}>
          <span className="font-data text-xs font-medium">{item.no}</span>
          <span className="text-[10px]">{locale === "zh" ? item.zh : item.en}</span>
        </Link>;
      })}
    </nav>
  );
}

export function AgentOsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { locale, setLocale, formatCurrency } = useI18n();
  const [overview, setOverview] = useState<AgentOSOverview | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);
  const current = useMemo(() => activeModule(pathname), [pathname]);
  useEffect(() => {
    void agentOSApi.overview().then(setOverview).catch(() => setOverview(null));
  }, [pathname]);
  const portfolio = overview?.portfolio && "total_value" in overview.portfolio ? overview.portfolio : null;
  return (
    <div className="flex h-dvh min-h-0 overflow-hidden bg-agent-canvas text-agent-text">
      <aside className="hidden w-[78px] shrink-0 flex-col items-center border-r border-agent-border bg-agent-chrome px-0 py-[18px] lg:flex">
        <Link href="/agent" className="mb-[22px] grid size-[34px] place-items-center rounded-lg bg-agent-mint font-data text-[15px] font-semibold text-agent-canvas">A</Link>
        <ModuleNavigation />
        <div className="mt-auto flex flex-col items-center gap-2"><span className="size-2 rounded-full bg-agent-mint shadow-[0_0_12px_var(--agent-mint)]" /><span className="font-data text-[9px] [writing-mode:vertical-rl] text-agent-dim">AGENT ONLINE</span></div>
      </aside>
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[60px] shrink-0 items-center gap-4 border-b border-agent-border bg-agent-chrome px-4 lg:px-[26px]">
          <Sheet open={navOpen} onOpenChange={setNavOpen}>
            <SheetTrigger asChild><Button variant="ghost" size="icon" className="lg:hidden"><Menu /></Button></SheetTrigger>
            <SheetContent side="left" className="w-[280px] border-agent-border bg-agent-chrome text-agent-text"><SheetHeader><SheetTitle className="text-left text-agent-text">KeelTrader AgentOS</SheetTitle></SheetHeader><div className="mt-6"><ModuleNavigation mobile close={() => setNavOpen(false)} /></div></SheetContent>
          </Sheet>
          <div className="flex min-w-0 items-baseline gap-2">
            <h1 className="truncate text-[17px] font-medium">{locale === "zh" ? current.zh : current.en}</h1>
            <span className="hidden font-data text-[10px] uppercase tracking-[.08em] text-agent-dim sm:inline">{current.en}</span>
          </div>
          <div className="hidden overflow-hidden rounded-md border border-agent-border md:flex">
            {["1M", "3M", "1Y", "3Y"].map((period) => <span key={period} className={`px-3 py-1.5 font-data text-[10px] ${period === "1Y" ? "bg-agent-mint text-agent-canvas" : "text-agent-dim"}`}>{period}</span>)}
          </div>
          <div className="ml-auto flex items-center gap-2 lg:gap-4">
            <div className="hidden items-center gap-2 font-data text-[10px] text-agent-muted xl:flex"><span className={`size-1.5 rounded-full ${overview?.data_status === "complete" ? "bg-agent-mint" : "bg-agent-amber"}`} />{overview?.as_of || "—"} · DATA</div>
            <Button onClick={() => router.push("/agent/research?report=1")} className="hidden bg-agent-mint text-agent-canvas hover:bg-agent-mint-bright sm:inline-flex"><FileDown />{locale === "zh" ? "生成报告" : "Export"}</Button>
            <button type="button" onClick={() => setLocale(locale === "zh" ? "en" : "zh")} className="rounded border border-agent-border px-2 py-1 font-data text-[10px] text-agent-muted hover:border-agent-mint hover:text-agent-mint">{locale === "zh" ? "EN" : "中"}</button>
            <div className="hidden gap-4 border-l border-agent-border pl-4 2xl:flex">
              <Metric label="TOTAL MV" value={portfolio ? formatCurrency(portfolio.total_value, portfolio.base_currency) : "—"} />
              <Metric label="STATUS" value={portfolio?.data_status?.toUpperCase() || "NO DATA"} accent={portfolio?.data_status === "complete"} />
            </div>
            <Button variant="ghost" size="icon" className="2xl:hidden" onClick={() => setAgentOpen(true)}><Bot /></Button>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto bg-agent-canvas">{children}</main>
      </section>
      <aside className="hidden w-[384px] shrink-0 2xl:block"><AgentDock /></aside>
      <Sheet open={agentOpen} onOpenChange={setAgentOpen}>
        <SheetContent side="right" className="w-full border-agent-border bg-agent-chrome p-0 text-agent-text sm:max-w-[420px]"><SheetHeader className="sr-only"><SheetTitle>Agent</SheetTitle></SheetHeader><AgentDock compact /></SheetContent>
      </Sheet>
    </div>
  );
}

function Metric({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return <div className="flex min-w-[88px] flex-col gap-0.5"><span className="font-data text-[8px] tracking-[.08em] text-agent-dim">{label}</span><span className={`truncate font-data text-xs ${accent ? "text-agent-mint" : "text-agent-text"}`}>{value}</span></div>;
}
