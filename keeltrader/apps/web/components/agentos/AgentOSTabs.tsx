'use client'

import {
  Activity,
  BookOpen,
  Check,
  ClipboardList,
  FlaskConical,
  Lightbulb,
  Loader2,
  Search,
  ShieldCheck,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  JsonBlock,
  ReportList,
  RiskNotice,
  Section,
  Stat,
} from '@/components/agentos/agentos-primitives'
import type { JsonMap, ResearchReportHit } from '@/lib/api/agentos'
import { formatDate } from '@/lib/agentos/format'
import type { useAgentOSDashboard } from '@/lib/agentos/use-agentos-dashboard'

type Dashboard = ReturnType<typeof useAgentOSDashboard>
type DashboardState = Dashboard['state']
type DashboardActions = Dashboard['actions']

export function AgentOSTabs({ state, actions }: { state: DashboardState; actions: DashboardActions }) {
  const latestBrief = state.briefs[0] || null
  const latestMemo = state.memos[0] || null
  const latestBacktest = state.backtests[0] || null

  return (
    <Tabs defaultValue="briefs" className="space-y-4">
      <TabsList className="flex h-auto flex-wrap justify-start">
        <TabsTrigger value="briefs"><Activity className="mr-2 h-4 w-4" />Briefs</TabsTrigger>
        <TabsTrigger value="research"><Search className="mr-2 h-4 w-4" />Research Lab</TabsTrigger>
        <TabsTrigger value="decisions"><ClipboardList className="mr-2 h-4 w-4" />Decisions</TabsTrigger>
        <TabsTrigger value="reviews"><ShieldCheck className="mr-2 h-4 w-4" />Reviews</TabsTrigger>
        <TabsTrigger value="strategy"><FlaskConical className="mr-2 h-4 w-4" />Strategy Lab</TabsTrigger>
        <TabsTrigger value="memory"><BookOpen className="mr-2 h-4 w-4" />Memory</TabsTrigger>
      </TabsList>

      <TabsContent value="briefs" className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Run Daily Brief</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-3 md:flex-row">
            <Input value={state.watchlist} onChange={(e) => actions.setWatchlist(e.target.value)} placeholder="000001.SZ 600519.SH" />
            <Button onClick={actions.runBrief} disabled={state.busy === 'brief'}>
              {state.busy === 'brief' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Activity className="mr-2 h-4 w-4" />}
              Generate
            </Button>
          </CardContent>
        </Card>
        {latestBrief ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{latestBrief.title}</CardTitle>
              <div className="text-xs text-muted-foreground">{formatDate(latestBrief.brief_date)}</div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm">{latestBrief.summary}</p>
              <div className="grid gap-3 md:grid-cols-2">
                {(latestBrief.signals || []).map((signal, idx) => {
                  const reports = Array.isArray(signal.reports) ? signal.reports as ResearchReportHit[] : []
                  return (
                    <div key={idx} className="rounded-md border p-3 text-sm">
                      <div className="font-medium">{String(signal.symbol || '')} {signal.name ? `· ${String(signal.name)}` : ''}</div>
                      <div className="mt-1 text-muted-foreground">
                        close {displayValue(signal.close)} · change {displayValue(signal.change_pct)}%
                      </div>
                      <div className="mt-1 text-muted-foreground">
                        reports {displayValue(signal.report_count ?? 0)}
                        {typeof signal.latest_report_date === 'string' ? ` · latest ${formatDate(signal.latest_report_date)}` : ''}
                      </div>
                      <Badge className="mt-2" variant="outline">{String(signal.signal || 'watch')}</Badge>
                      <ReportList reports={reports} compact />
                    </div>
                  )
                })}
              </div>
              <RiskNotice risks={latestBrief.risks || []} />
            </CardContent>
          </Card>
        ) : <EmptyState title="No briefs yet." />}
      </TabsContent>

      <TabsContent value="research" className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Deep Research</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-3 md:flex-row">
            <Input value={state.researchSymbol} onChange={(e) => actions.setResearchSymbol(e.target.value)} placeholder="000001.SZ" />
            <Button onClick={actions.runResearch} disabled={state.busy === 'research'}>
              {state.busy === 'research' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              Run
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Report KB Search</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-3 md:flex-row">
              <Input value={state.reportQuery} onChange={(e) => actions.setReportQuery(e.target.value)} placeholder="平安银行 投资 研报" />
              <Button onClick={actions.searchReports} disabled={state.busy === 'reports'}>
                {state.busy === 'reports' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookOpen className="mr-2 h-4 w-4" />}
                Search Reports
              </Button>
            </div>
            <ReportList reports={state.reportHits} />
          </CardContent>
        </Card>
        {latestMemo ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{latestMemo.title}</CardTitle>
              <div className="flex gap-2"><Badge>{latestMemo.recommendation || 'research_only'}</Badge><Badge variant="outline">{latestMemo.symbol}</Badge></div>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <Section title="Thesis" value={latestMemo.thesis} />
                <Section title="Bull Case" value={latestMemo.bull_case} />
                <Section title="Bear Case" value={latestMemo.bear_case} />
                <Section title="Red Team" value={latestMemo.red_team} />
                <Section title="Risk View" value={latestMemo.risk_view} />
              </div>
              <div>
                <Label>Analyst Views</Label>
                <JsonBlock data={latestMemo.analyst_views} />
              </div>
              <div className="md:col-span-2">
                <Label>Related Reports</Label>
                <ReportList reports={memoReports(latestMemo.analyst_views)} />
              </div>
            </CardContent>
          </Card>
        ) : <EmptyState title="No research memos yet." />}
      </TabsContent>

      <TabsContent value="decisions" className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Record Decision</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 md:grid-cols-4">
              <Input value={state.decisionForm.symbol} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, symbol: e.target.value }))} placeholder="Symbol" />
              <Input value={state.decisionForm.action} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, action: e.target.value }))} placeholder="watch/buy/sell/hold" />
              <Input type="number" value={state.decisionForm.confidence} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, confidence: Number(e.target.value) }))} placeholder="Confidence" />
              <Input value={state.decisionForm.human_decision} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, human_decision: e.target.value }))} placeholder="pending/accepted/rejected" />
            </div>
            <Textarea value={state.decisionForm.thesis} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, thesis: e.target.value }))} placeholder="Decision thesis" />
            <Input value={state.decisionForm.human_reason} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, human_reason: e.target.value }))} placeholder="Human reason" />
            <Button onClick={actions.recordDecision} disabled={state.busy === 'decision'}>
              {state.busy === 'decision' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ClipboardList className="mr-2 h-4 w-4" />}
              Save Decision
            </Button>
          </CardContent>
        </Card>
        <div className="space-y-2">
          {state.decisions.length ? state.decisions.map((item) => (
            <Card key={item.id}>
              <CardContent className="flex flex-col gap-2 p-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="font-medium">{item.symbol} · {item.action}</div>
                  <div className="mt-1 text-sm text-muted-foreground">{item.thesis}</div>
                  <div className="mt-2 flex gap-2"><Badge>{item.human_decision}</Badge><Badge variant="outline">{item.status}</Badge></div>
                </div>
                <div className="text-xs text-muted-foreground">{formatDate(item.created_at)}</div>
              </CardContent>
            </Card>
          )) : <EmptyState title="No decisions yet." />}
        </div>
      </TabsContent>

      <TabsContent value="reviews" className="space-y-4">
        <Button onClick={actions.runReview} disabled={state.busy === 'review'}>
          {state.busy === 'review' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}
          Run Weekly Review
        </Button>
        <div className="space-y-2">
          {state.lessons.length ? state.lessons.map((item) => (
            <Card key={item.id}>
              <CardContent className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.title}</div>
                    <p className="mt-1 text-sm text-muted-foreground">{item.lesson}</p>
                  </div>
                  <Button size="sm" onClick={() => actions.approveLesson(item.id)} disabled={state.busy === item.id}>
                    <Check className="mr-2 h-4 w-4" />
                    Approve
                  </Button>
                </div>
                <JsonBlock data={item.evidence} />
              </CardContent>
            </Card>
          )) : <EmptyState title="No pending lessons." />}
        </div>
      </TabsContent>

      <TabsContent value="strategy" className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Strategy Hypothesis</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Input value={state.hypothesisForm.name} onChange={(e) => actions.setHypothesisForm((p) => ({ ...p, name: e.target.value }))} placeholder="Hypothesis name" />
            <Textarea value={state.hypothesisForm.hypothesis} onChange={(e) => actions.setHypothesisForm((p) => ({ ...p, hypothesis: e.target.value }))} placeholder="Testable hypothesis" />
            <Input value={state.hypothesisForm.rationale} onChange={(e) => actions.setHypothesisForm((p) => ({ ...p, rationale: e.target.value }))} placeholder="Economic rationale" />
            <Input value={state.hypothesisForm.asset_universe} onChange={(e) => actions.setHypothesisForm((p) => ({ ...p, asset_universe: e.target.value }))} placeholder="Asset universe" />
            <Button onClick={actions.createHypothesis} disabled={state.busy === 'hypothesis'}>
              <Lightbulb className="mr-2 h-4 w-4" />
              Create Hypothesis
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Guarded Backtest</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            <Input value={state.backtestSymbol} onChange={(e) => actions.setBacktestSymbol(e.target.value)} placeholder="000001.SZ" />
            <select className="rounded-md border bg-background px-3 py-2 text-sm" value={state.selectedHypothesisId} onChange={(e) => actions.setSelectedHypothesisId(e.target.value)}>
              <option value="">No hypothesis</option>
              {state.hypotheses.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <Button onClick={actions.runBacktest} disabled={state.busy === 'backtest'}>
              {state.busy === 'backtest' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FlaskConical className="mr-2 h-4 w-4" />}
              Run MA 20/60
            </Button>
          </CardContent>
        </Card>
        {latestBacktest ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{latestBacktest.symbol} · {latestBacktest.strategy}</CardTitle>
              <Badge variant={latestBacktest.passed_gate ? 'default' : 'outline'}>{latestBacktest.passed_gate ? 'Passed Gate' : 'Not Passed'}</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-5">
                <Stat label="Trades" value={displayValue(latestBacktest.metrics.total_trades)} />
                <Stat label="Return %" value={displayValue(latestBacktest.metrics.total_return_pct)} />
                <Stat label="Max DD %" value={displayValue(latestBacktest.metrics.max_drawdown_pct)} />
                <Stat label="Sharpe" value={displayValue(latestBacktest.metrics.sharpe_ratio)} />
                <Stat label="DSR Proxy" value={displayValue(latestBacktest.metrics.deflated_sharpe_proxy)} />
              </div>
              <JsonBlock data={latestBacktest.trades?.slice(0, 20) || []} />
            </CardContent>
          </Card>
        ) : <EmptyState title="No backtests yet." />}
      </TabsContent>

      <TabsContent value="memory" className="space-y-3">
        {state.memory.length ? state.memory.map((item) => (
          <Card key={item.id}>
            <CardContent className="p-4">
              <div className="font-medium">{item.title}</div>
              <p className="mt-1 text-sm text-muted-foreground">{item.lesson}</p>
              <div className="mt-2 text-xs text-muted-foreground">Approved {formatDate(item.approved_at)}</div>
            </CardContent>
          </Card>
        )) : <EmptyState title="No approved lessons yet." />}
      </TabsContent>
    </Tabs>
  )
}

function displayValue(value: unknown): string | number {
  if (typeof value === 'string' || typeof value === 'number') return value
  if (typeof value === 'boolean') return String(value)
  return '-'
}

function memoReports(views: JsonMap): ResearchReportHit[] {
  const researchReports = views.research_reports
  if (!researchReports || typeof researchReports !== 'object' || Array.isArray(researchReports)) {
    return []
  }
  const reports = researchReports.reports
  return Array.isArray(reports) ? reports as ResearchReportHit[] : []
}
