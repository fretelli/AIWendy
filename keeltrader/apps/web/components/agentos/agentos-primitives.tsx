'use client'

import { AlertTriangle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import type { AgentOSHealth, ResearchReportHit } from '@/lib/api/agentos'
import { formatDate } from '@/lib/agentos/format'

export function Stat({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value ?? '-'}</div>
    </div>
  )
}

export function EmptyState({ title }: { title: string }) {
  return <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">{title}</div>
}

export function JsonBlock({ data }: { data: unknown }) {
  return (
    <pre className="max-h-72 overflow-auto rounded-md bg-muted p-3 text-xs">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

export function Section({ title, value }: { title: string; value?: string | null }) {
  return (
    <div>
      <Label>{title}</Label>
      <div className="mt-1 rounded-md border p-3 text-sm text-muted-foreground">{value || '-'}</div>
    </div>
  )
}

export function StatusBadges({ health }: { health: AgentOSHealth | null }) {
  const ok = health?.status === 'ok'
  const engineStatus = typeof health?.engine?.status === 'string' ? health.engine.status : 'unknown'
  const reportKbReachable = health?.report_kb?.reachable === true

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge variant={ok ? 'default' : 'destructive'}>{ok ? 'API OK' : 'API Down'}</Badge>
      <Badge variant={engineStatus === 'running' ? 'secondary' : 'outline'}>Engine {engineStatus}</Badge>
      <Badge variant={reportKbReachable ? 'secondary' : 'outline'}>
        Report KB {reportKbReachable ? 'OK' : 'off'}
      </Badge>
      <Badge variant="outline">No Tushare token</Badge>
    </div>
  )
}

export function RiskNotice({ risks }: { risks: string[] }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
      <AlertTriangle className="mr-2 inline h-4 w-4" />
      {risks.join(' ')}
    </div>
  )
}

export function ReportList({ reports, compact = false }: { reports: ResearchReportHit[]; compact?: boolean }) {
  if (!reports?.length) {
    return compact ? null : <EmptyState title="No related reports." />
  }

  return (
    <div className={compact ? 'mt-3 space-y-2' : 'mt-2 space-y-2'}>
      {reports.slice(0, compact ? 3 : 8).map((item, index) => (
        <div key={`${item.report_id || index}-${item.section_id || index}`} className="rounded-md border p-3 text-sm">
          <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
            <div className="font-medium">{item.title || 'Untitled report'}</div>
            <div className="text-xs text-muted-foreground">{formatDate(item.report_date)}</div>
          </div>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
            {item.broker ? <span>{item.broker}</span> : null}
            {typeof item.score === 'number' ? <span>score {item.score.toFixed(3)}</span> : null}
            {item.report_id ? <span>{item.report_id.slice(0, 8)}</span> : null}
          </div>
          {!compact && item.excerpt ? (
            <p className="mt-2 line-clamp-3 text-xs text-muted-foreground">{item.excerpt}</p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
