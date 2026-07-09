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
import { useI18n } from '@/lib/i18n/provider'

type Dashboard = ReturnType<typeof useAgentOSDashboard>
type DashboardState = Dashboard['state']
type DashboardActions = Dashboard['actions']

export function AgentOSTabs({ state, actions }: { state: DashboardState; actions: DashboardActions }) {
  const { t } = useI18n()
  const latestBrief = state.briefs[0] || null
  const latestMemo = state.memos[0] || null
  const latestValidation = state.validations[0] || null

  return (
    <Tabs defaultValue="briefs" className="space-y-4">
      <TabsList className="flex h-auto flex-wrap justify-start">
        <TabsTrigger value="briefs"><Activity className="mr-2 h-4 w-4" />{t('agentos.tabs.briefs')}</TabsTrigger>
        <TabsTrigger value="research"><Search className="mr-2 h-4 w-4" />{t('agentos.tabs.research')}</TabsTrigger>
        <TabsTrigger value="decisions"><ClipboardList className="mr-2 h-4 w-4" />{t('agentos.tabs.decisions')}</TabsTrigger>
        <TabsTrigger value="reviews"><ShieldCheck className="mr-2 h-4 w-4" />{t('agentos.tabs.reviews')}</TabsTrigger>
        <TabsTrigger value="strategy"><FlaskConical className="mr-2 h-4 w-4" />{t('agentos.tabs.strategy')}</TabsTrigger>
        <TabsTrigger value="memory"><BookOpen className="mr-2 h-4 w-4" />{t('agentos.tabs.memory')}</TabsTrigger>
      </TabsList>

      <TabsContent value="briefs" className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-base">{t('agentos.briefs.runTitle')}</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-3 md:flex-row">
            <Input value={state.watchlist} onChange={(e) => actions.setWatchlist(e.target.value)} placeholder="000001.SZ 600519.SH" />
            <Button onClick={actions.runBrief} disabled={state.busy === 'brief'}>
              {state.busy === 'brief' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Activity className="mr-2 h-4 w-4" />}
              {t('agentos.briefs.generate')}
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
                        {t('agentos.briefs.close')} {displayValue(signal.close)} · {t('agentos.briefs.change')} {displayValue(signal.change_pct)}%
                      </div>
                      <div className="mt-1 text-muted-foreground">
                        {t('agentos.briefs.reports')} {displayValue(signal.report_count ?? 0)}
                        {typeof signal.latest_report_date === 'string' ? ` · ${t('agentos.briefs.latest')} ${formatDate(signal.latest_report_date)}` : ''}
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
        ) : <EmptyState title={t('agentos.empty.briefs')} />}
      </TabsContent>

      <TabsContent value="research" className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-base">{t('agentos.research.deepTitle')}</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-3 md:flex-row">
            <Input value={state.researchSymbol} onChange={(e) => actions.setResearchSymbol(e.target.value)} placeholder="000001.SZ" />
            <Button onClick={actions.runResearch} disabled={state.busy === 'research'}>
              {state.busy === 'research' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              {t('agentos.research.run')}
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">{t('agentos.research.reportSearchTitle')}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-3 md:flex-row">
              <Input value={state.reportQuery} onChange={(e) => actions.setReportQuery(e.target.value)} placeholder="平安银行 投资 研报" />
              <Button onClick={actions.searchReports} disabled={state.busy === 'reports'}>
                {state.busy === 'reports' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookOpen className="mr-2 h-4 w-4" />}
                {t('agentos.research.searchReports')}
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
                <Section title={t('agentos.research.thesis')} value={latestMemo.thesis} />
                <Section title={t('agentos.research.bullCase')} value={latestMemo.bull_case} />
                <Section title={t('agentos.research.bearCase')} value={latestMemo.bear_case} />
                <Section title={t('agentos.research.redTeam')} value={latestMemo.red_team} />
                <Section title={t('agentos.research.riskView')} value={latestMemo.risk_view} />
              </div>
              <div>
                <Label>{t('agentos.research.analystViews')}</Label>
                <JsonBlock data={latestMemo.analyst_views} />
              </div>
              <div className="md:col-span-2">
                <Label>{t('agentos.research.relatedReports')}</Label>
                <ReportList reports={memoReports(latestMemo.analyst_views)} />
              </div>
            </CardContent>
          </Card>
        ) : <EmptyState title={t('agentos.empty.research')} />}
      </TabsContent>

      <TabsContent value="decisions" className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-base">{t('agentos.decisions.recordTitle')}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 md:grid-cols-4">
              <Input value={state.decisionForm.symbol} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, symbol: e.target.value }))} placeholder={t('agentos.decisions.symbol')} />
              <Input value={state.decisionForm.action} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, action: e.target.value }))} placeholder={t('agentos.decisions.actionPlaceholder')} />
              <Input type="number" value={state.decisionForm.confidence} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, confidence: Number(e.target.value) }))} placeholder={t('agentos.decisions.confidence')} />
              <Input value={state.decisionForm.human_decision} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, human_decision: e.target.value }))} placeholder={t('agentos.decisions.humanDecisionPlaceholder')} />
            </div>
            <Textarea value={state.decisionForm.thesis} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, thesis: e.target.value }))} placeholder={t('agentos.decisions.thesisPlaceholder')} />
            <Input value={state.decisionForm.human_reason} onChange={(e) => actions.setDecisionForm((p) => ({ ...p, human_reason: e.target.value }))} placeholder={t('agentos.decisions.humanReason')} />
            <Button onClick={actions.recordDecision} disabled={state.busy === 'decision'}>
              {state.busy === 'decision' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ClipboardList className="mr-2 h-4 w-4" />}
              {t('agentos.decisions.save')}
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
          )) : <EmptyState title={t('agentos.empty.decisions')} />}
        </div>
      </TabsContent>

      <TabsContent value="reviews" className="space-y-4">
        <Button onClick={actions.runReview} disabled={state.busy === 'review'}>
          {state.busy === 'review' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}
          {t('agentos.reviews.run')}
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
                    {t('agentos.reviews.approve')}
                  </Button>
                </div>
                <JsonBlock data={item.evidence} />
              </CardContent>
            </Card>
          )) : <EmptyState title={t('agentos.empty.pendingLessons')} />}
        </div>
      </TabsContent>

      <TabsContent value="strategy" className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-base">{t('agentos.strategy.hypothesisTitle')}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Input value={state.hypothesisForm.name} onChange={(e) => actions.setHypothesisForm((p) => ({ ...p, name: e.target.value }))} placeholder={t('agentos.strategy.hypothesisName')} />
            <Textarea value={state.hypothesisForm.hypothesis} onChange={(e) => actions.setHypothesisForm((p) => ({ ...p, hypothesis: e.target.value }))} placeholder={t('agentos.strategy.testableHypothesis')} />
            <Input value={state.hypothesisForm.rationale} onChange={(e) => actions.setHypothesisForm((p) => ({ ...p, rationale: e.target.value }))} placeholder={t('agentos.strategy.rationale')} />
            <Input value={state.hypothesisForm.asset_universe} onChange={(e) => actions.setHypothesisForm((p) => ({ ...p, asset_universe: e.target.value }))} placeholder={t('agentos.strategy.assetUniverse')} />
            <Button onClick={actions.createHypothesis} disabled={state.busy === 'hypothesis'}>
              <Lightbulb className="mr-2 h-4 w-4" />
              {t('agentos.strategy.createHypothesis')}
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">{t('agentos.strategy.validationTitle')}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <Input value={state.validationForm.symbol} onChange={(e) => actions.setValidationForm((p) => ({ ...p, symbol: e.target.value }))} placeholder="000001.SZ" />
              <select className="rounded-md border bg-background px-3 py-2 text-sm" value={state.validationForm.conclusion} onChange={(e) => actions.setValidationForm((p) => ({ ...p, conclusion: e.target.value }))}>
                <option value="observe">{t('agentos.strategy.observe')}</option>
                <option value="supported">{t('agentos.strategy.supported')}</option>
                <option value="rejected">{t('agentos.strategy.rejected')}</option>
                <option value="revise">{t('agentos.strategy.revise')}</option>
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm" value={state.selectedHypothesisId} onChange={(e) => actions.setSelectedHypothesisId(e.target.value)}>
                <option value="">{t('agentos.strategy.noHypothesis')}</option>
                {state.hypotheses.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </div>
            <Textarea value={state.validationForm.evidence} onChange={(e) => actions.setValidationForm((p) => ({ ...p, evidence: e.target.value }))} placeholder={t('agentos.strategy.evidencePlaceholder')} />
            <Textarea value={state.validationForm.risks} onChange={(e) => actions.setValidationForm((p) => ({ ...p, risks: e.target.value }))} placeholder={t('agentos.strategy.risksPlaceholder')} />
            <Input value={state.validationForm.notes} onChange={(e) => actions.setValidationForm((p) => ({ ...p, notes: e.target.value }))} placeholder={t('agentos.strategy.validationNotes')} />
            <Button onClick={actions.recordValidation} disabled={state.busy === 'validation'}>
              {state.busy === 'validation' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FlaskConical className="mr-2 h-4 w-4" />}
              {t('agentos.strategy.recordValidation')}
            </Button>
          </CardContent>
        </Card>
        {latestValidation ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{latestValidation.symbol} · {t('agentos.strategy.fundamentalValidation')}</CardTitle>
              <Badge variant={latestValidation.passed_gate ? 'default' : 'outline'}>{latestValidation.passed_gate ? t('agentos.strategy.passedGate') : t('agentos.strategy.notPassed')}</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-5">
                <Stat label={t('agentos.strategy.conclusion')} value={displayValue(latestValidation.metrics.conclusion)} />
                <Stat label={t('agentos.strategy.evidenceCount')} value={displayValue(latestValidation.metrics.evidence_count)} />
                <Stat label={t('agentos.strategy.riskCount')} value={displayValue(latestValidation.metrics.risk_count)} />
                <Stat label={t('agentos.strategy.hasFinancials')} value={displayValue(latestValidation.metrics.has_recent_financials)} />
                <Stat label={t('agentos.strategy.priceContext')} value={displayValue(latestValidation.metrics.has_latest_price_context)} />
              </div>
              <p className="text-xs text-muted-foreground">
                {t('agentos.strategy.validationNotice')}
              </p>
              <JsonBlock data={latestValidation.params} />
            </CardContent>
          </Card>
        ) : <EmptyState title={t('agentos.empty.validations')} />}
        <Card>
          <CardHeader><CardTitle className="text-base">{t('agentos.strategy.hypothesisList')}</CardTitle></CardHeader>
          <CardContent>
            <select className="rounded-md border bg-background px-3 py-2 text-sm" value={state.selectedHypothesisId} onChange={(e) => actions.setSelectedHypothesisId(e.target.value)}>
              <option value="">{t('agentos.strategy.noHypothesis')}</option>
              {state.hypotheses.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="memory" className="space-y-3">
        {state.memory.length ? state.memory.map((item) => (
          <Card key={item.id}>
            <CardContent className="p-4">
              <div className="font-medium">{item.title}</div>
              <p className="mt-1 text-sm text-muted-foreground">{item.lesson}</p>
              <div className="mt-2 text-xs text-muted-foreground">{t('agentos.memory.approved')} {formatDate(item.approved_at)}</div>
            </CardContent>
          </Card>
        )) : <EmptyState title={t('agentos.empty.approvedLessons')} />}
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
