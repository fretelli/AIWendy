'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, CircleDollarSign, Landmark, Radar, RefreshCw, ShipWheel, Waves } from 'lucide-react'
import type { ReactNode } from 'react'

import { KeelMark, ThemeMenu } from '@/components/keel-brand'
import { Button } from '@/components/ui/button'

const sections = [
  { href: '/agent/capital', label: 'A股资金', icon: Waves },
  { href: '/agent/capital/macro', label: '宏观', icon: Landmark },
  { href: '/agent/capital/futures', label: '期货', icon: BarChart3 },
  { href: '/agent/capital/options', label: '期权', icon: CircleDollarSign },
]

export function MarketShell({ title, subtitle, refreshing, onRefresh, children }: {
  title: string; subtitle: string; refreshing?: boolean; onRefresh?: () => void; children: ReactNode
}) {
  const pathname = usePathname()
  return <div className="h-full min-h-0 overflow-y-auto bg-background/80">
    <header className="research-bearing sticky top-0 z-30 border-b bg-card/95 shadow-sm backdrop-blur">
      <div className="flex min-h-16 items-center gap-2 px-3 sm:px-5">
        <div className="hidden border-r pr-4 sm:block"><KeelMark /></div>
        <div className="min-w-0 flex-1"><h1 className="font-display text-lg font-semibold">{title}</h1><p className="truncate text-[10px] text-muted-foreground">{subtitle}</p></div>
        {onRefresh && <Button size="sm" variant="outline" disabled={refreshing} onClick={onRefresh}><RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />刷新</Button>}
        <Button asChild size="sm" variant="outline"><Link href="/agent/holders"><Radar className="mr-1.5 h-4 w-4" /><span className="hidden md:inline">股东雷达</span></Link></Button>
        <Button asChild size="sm" variant="outline"><Link href="/agent"><ShipWheel className="mr-1.5 h-4 w-4" /><span className="hidden md:inline">研究台</span></Link></Button>
        <ThemeMenu />
      </div>
      <MarketNavigation pathname={pathname} />
    </header>
    <main className="mx-auto max-w-[1580px] space-y-5 p-4 md:p-7">{children}</main>
  </div>
}

export function MarketNavigation({ pathname: suppliedPathname }: { pathname?: string }) {
  const currentPathname = usePathname()
  const pathname = suppliedPathname || currentPathname
  return <nav aria-label="市场数据分区" className="flex overflow-x-auto border-t bg-card/95 px-3 sm:px-5">
    {sections.map(({ href, label, icon: Icon }) => {
      const active = href === '/agent/capital' ? pathname === href : pathname.startsWith(href)
      return <Link key={href} href={href} className={`relative flex shrink-0 items-center gap-2 px-4 py-3 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring ${active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
        <Icon className="h-3.5 w-3.5" />{label}{active && <span className="absolute inset-x-3 bottom-0 h-0.5 bg-[hsl(var(--copper-foreground))]" />}
      </Link>
    })}
  </nav>
}

export function DataLedger({ source, start, end, points, scope }: { source: string; start?: string; end?: string; points?: number; scope: string }) {
  return <div className="grid gap-px overflow-hidden rounded-xl border bg-border text-[10px] sm:grid-cols-4">
    <LedgerCell label="来源" value={source} /><LedgerCell label="数据范围" value={start && end ? `${start} — ${end}` : '不可用'} />
    <LedgerCell label="数据点" value={points === undefined ? '—' : String(points)} /><LedgerCell label="覆盖口径" value={scope} />
  </div>
}

function LedgerCell({ label, value }: { label: string; value: string }) { return <div className="min-w-0 bg-card/90 px-4 py-3"><p className="text-muted-foreground">{label}</p><p className="mt-1 truncate font-data text-foreground" title={value}>{value}</p></div> }
