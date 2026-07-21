"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  Command,
  Radar,
  Search,
  ShipWheel,
  Waves,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const destinations = [
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
];

export function ResearchOsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(),
    router = useRouter();
  const [open, setOpen] = useState(false),
    [query, setQuery] = useState("");
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
        {destinations.map(({ href, label, icon: Icon }) => {
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
      </nav>
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
                placeholder="前往研究、股东或市场工作区…"
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
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
