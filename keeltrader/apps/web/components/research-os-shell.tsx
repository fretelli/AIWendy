"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  Command,
  Radar,
  BellRing,
  BookOpen,
  Search,
  ShipWheel,
  Route,
  Menu,
  Waves,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { agentPlatformApi, type GlobalSearchResult } from "@/lib/api/agent-platform";

const destinations = [
  {
    href: "/agent/today",
    label: "今日",
    detail: "变化、复核与数据源值守",
    icon: BellRing,
  },
  {
    href: "/agent/theses",
    label: "论点",
    detail: "证据、版本与证伪日志",
    icon: BookOpen,
  },
  {
    href: "/agent",
    label: "研究台",
    detail: "会话、证据与公司档案",
    icon: ShipWheel,
  },
  {
    href: "/agent/holders",
    label: "股东雷达",
    detail: "关注股东与持仓变化",
    icon: Radar,
  },
  {
    href: "/agent/market/capital",
    label: "市场",
    detail: "资金、利率债券、宏观、期货、期权与机会",
    icon: Waves,
  },
  {
    href: "/agent/allocation",
    label: "资产配置",
    detail: "资金约束、币种暴露与不可变配置版本",
    icon: Route,
  },
];

const mobilePrimary = ["/agent/today", "/agent", "/agent/allocation", "/agent/market/capital"]
  .map((href) => destinations.find((item) => item.href === href)!)
  .filter(Boolean);
const mobileMore = destinations.filter((item) => !mobilePrimary.includes(item));

export function ResearchOsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(),
    router = useRouter();
  const [open, setOpen] = useState(false),
    [query, setQuery] = useState(""),
    [moreOpen, setMoreOpen] = useState(false);
  const [researchResults, setResearchResults] = useState<GlobalSearchResult[]>([]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => {
    if (!open || query.trim().length < 2) return;
    const timer = window.setTimeout(() => {
      agentPlatformApi.globalSearch(query.trim()).then((result) => setResearchResults(result.items)).catch(() => setResearchResults([]));
    }, 240);
    return () => window.clearTimeout(timer);
  }, [open, query]);
  const matches = useMemo(
    () =>
      destinations.filter((item) =>
        `${item.label}${item.detail}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [query],
  );
  return (
    <div className="flex h-dvh min-h-0 overflow-hidden bg-background">
      <aside className="research-bearing hidden w-[76px] shrink-0 flex-col border-r bg-card/95 lg:flex">
        <div className="grid h-16 place-items-center border-b">
          <span className="font-display text-xl text-[hsl(var(--copper-foreground))]">
            K
          </span>
        </div>
        <nav
          className="flex flex-1 flex-col gap-2 p-2"
          aria-label="研究操作系统"
        >
          {destinations.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/agent" ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                title={label}
                className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[10px] transition ${active ? "bg-[hsl(var(--accent)/.12)] text-foreground shadow-[inset_2px_0_hsl(var(--copper))]" : "text-muted-foreground hover:bg-secondary hover:text-foreground"}`}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
        <button
          aria-label="打开全局命令"
          onClick={() => setOpen(true)}
          className="m-2 grid h-11 place-items-center rounded-xl border text-muted-foreground hover:bg-secondary"
        >
          <Command className="h-4 w-4" />
        </button>
      </aside>
      <div className="min-w-0 flex-1 pb-14 lg:pb-0">{children}</div>
      <nav className="fixed inset-x-0 bottom-0 z-50 flex h-14 border-t bg-card/95 backdrop-blur lg:hidden">
        {mobilePrimary.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/agent" ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-1 flex-col items-center justify-center gap-1 text-[10px] ${active ? "text-[hsl(var(--copper-foreground))]" : "text-muted-foreground"}`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
        <button type="button" onClick={() => setMoreOpen(true)} className="flex flex-1 flex-col items-center justify-center gap-1 text-[10px] text-muted-foreground">
          <Menu className="h-4 w-4" />更多
        </button>
      </nav>
      {moreOpen && <div className="fixed inset-0 z-[75] bg-[hsl(var(--deep-sounding)/.45)] lg:hidden" onClick={() => setMoreOpen(false)}><section className="absolute inset-x-3 bottom-16 rounded-2xl border bg-popover p-2 shadow-2xl" onClick={(event) => event.stopPropagation()}>{mobileMore.map(({ href, label, detail, icon: Icon }) => <Link key={href} href={href} onClick={() => setMoreOpen(false)} className="flex items-center gap-3 rounded-xl px-3 py-3 hover:bg-secondary"><span className="grid h-9 w-9 place-items-center rounded-lg border bg-card"><Icon className="h-4 w-4" /></span><span><span className="block text-sm font-medium">{label}</span><span className="text-[10px] text-muted-foreground">{detail}</span></span></Link>)}<button type="button" onClick={() => { setMoreOpen(false); setOpen(true); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left hover:bg-secondary"><span className="grid h-9 w-9 place-items-center rounded-lg border bg-card"><Command className="h-4 w-4" /></span><span><span className="block text-sm font-medium">全局搜索</span><span className="text-[10px] text-muted-foreground">搜索会话、公司、股东、论点与配置</span></span></button></section></div>}
      {open && (
        <div
          className="fixed inset-0 z-[80] bg-[hsl(var(--deep-sounding)/.58)] p-4 pt-[12vh] backdrop-blur-sm"
          onMouseDown={() => setOpen(false)}
        >
          <section
            className="mx-auto max-w-xl overflow-hidden rounded-2xl border bg-popover shadow-2xl"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b px-4">
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索会话、公司、股东、论点、机会与研报…"
                className="h-14 flex-1 bg-transparent text-sm outline-none"
              />
              <button onClick={() => setOpen(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-2">
              {matches.map(({ href, label, detail, icon: Icon }) => (
                <button
                  key={href}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left hover:bg-secondary"
                  onClick={() => {
                    router.push(href);
                    setOpen(false);
                    setQuery("");
                  }}
                >
                  <span className="grid h-9 w-9 place-items-center rounded-lg border bg-card">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span>
                    <span className="block text-sm font-medium">{label}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {detail}
                    </span>
                  </span>
                  <BarChart3 className="ml-auto h-3.5 w-3.5 text-muted-foreground" />
                </button>
              ))}
              {query.trim().length >= 2 && researchResults.length > 0 && <div className="mt-2 border-t pt-2"><p className="px-3 py-2 text-[9px] font-semibold uppercase tracking-[.16em] text-muted-foreground">研究对象</p>{researchResults.map((item) => <button key={`${item.type}-${item.id}`} className="flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-secondary" onClick={() => { router.push(item.href); setOpen(false); setQuery(""); }}><span className="mt-1 rounded border px-1.5 py-0.5 font-data text-[8px] uppercase text-muted-foreground">{item.type}</span><span className="min-w-0"><span className="block truncate text-xs font-medium">{item.title}</span><span className="mt-1 block text-[10px] text-muted-foreground">{item.navigation_only ? "仅用于导航，不构成公司研报证据" : item.subtitle}</span></span></button>)}</div>}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
