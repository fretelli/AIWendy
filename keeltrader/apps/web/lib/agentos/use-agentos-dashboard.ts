'use client'

import { useCallback, useState } from 'react'
import { toast } from 'sonner'

import {
  agentosApi,
  type AgentOSHealth,
  type FundamentalValidation,
  type InvestmentBrief,
  type InvestmentDecision,
  type InvestmentMemo,
  type ReviewLesson,
  type ResearchReportHit,
  type StrategyHypothesis,
} from '@/lib/api/agentos'
import { errorMessage, splitSymbols } from '@/lib/agentos/format'

export type DecisionFormState = {
  symbol: string
  action: string
  thesis: string
  confidence: number
  human_decision: string
  human_reason: string
}

export type HypothesisFormState = {
  name: string
  hypothesis: string
  rationale: string
  asset_universe: string
}

export type ValidationFormState = {
  symbol: string
  conclusion: string
  evidence: string
  risks: string
  notes: string
}

export function useAgentOSDashboard() {
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [health, setHealth] = useState<AgentOSHealth | null>(null)
  const [briefs, setBriefs] = useState<InvestmentBrief[]>([])
  const [memos, setMemos] = useState<InvestmentMemo[]>([])
  const [decisions, setDecisions] = useState<InvestmentDecision[]>([])
  const [lessons, setLessons] = useState<ReviewLesson[]>([])
  const [memory, setMemory] = useState<ReviewLesson[]>([])
  const [hypotheses, setHypotheses] = useState<StrategyHypothesis[]>([])
  const [validations, setValidations] = useState<FundamentalValidation[]>([])
  const [reportHits, setReportHits] = useState<ResearchReportHit[]>([])

  const [watchlist, setWatchlist] = useState('000001.SZ 600519.SH')
  const [researchSymbol, setResearchSymbol] = useState('000001.SZ')
  const [reportQuery, setReportQuery] = useState('平安银行 投资 研报')
  const [decisionForm, setDecisionForm] = useState<DecisionFormState>({
    symbol: '000001.SZ',
    action: 'watch',
    thesis: '',
    confidence: 0,
    human_decision: 'pending',
    human_reason: '',
  })
  const [hypothesisForm, setHypothesisForm] = useState<HypothesisFormState>({
    name: '',
    hypothesis: '',
    rationale: '',
    asset_universe: '000001.SZ',
  })
  const [validationForm, setValidationForm] = useState<ValidationFormState>({
    symbol: '000001.SZ',
    conclusion: 'observe',
    evidence: '',
    risks: '',
    notes: '',
  })
  const [selectedHypothesisId, setSelectedHypothesisId] = useState('')

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [h, b, r, d, l, m, hyp, validationResult] = await Promise.all([
        agentosApi.health(),
        agentosApi.listBriefs(),
        agentosApi.listResearch(),
        agentosApi.listDecisions(),
        agentosApi.listLessons(false),
        agentosApi.listLessons(true),
        agentosApi.listHypotheses(),
        agentosApi.listValidations(),
      ])
      setHealth(h)
      setBriefs(b.briefs || [])
      setMemos(r.memos || [])
      setDecisions(d.decisions || [])
      setLessons(l.lessons || [])
      setMemory(m.lessons || [])
      setHypotheses(hyp.hypotheses || [])
      setValidations(validationResult.validations || [])
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to load AgentOS'))
    } finally {
      setLoading(false)
    }
  }, [])

  const runBrief = useCallback(async () => {
    setBusy('brief')
    try {
      await agentosApi.runBrief(splitSymbols(watchlist))
      toast.success('Brief generated')
      await refresh()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }, [refresh, watchlist])

  const runResearch = useCallback(async () => {
    setBusy('research')
    try {
      const result = await agentosApi.runResearch(researchSymbol, 'cn_equity')
      setDecisionForm((prev) => ({
        ...prev,
        symbol: result.memo.symbol,
        action: 'watch',
        thesis: result.memo.thesis,
        confidence: result.memo.confidence || 0,
      }))
      toast.success('Research memo generated')
      await refresh()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }, [refresh, researchSymbol])

  const searchReports = useCallback(async () => {
    if (!reportQuery.trim()) {
      toast.error('Report query is required')
      return
    }
    setBusy('reports')
    try {
      const result = await agentosApi.searchReports({ query: reportQuery, top_k: 8 })
      setReportHits(result.reports || [])
      toast.success('Reports searched')
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }, [reportQuery])

  const recordDecision = useCallback(async () => {
    if (!decisionForm.thesis.trim()) {
      toast.error('Thesis is required')
      return
    }
    setBusy('decision')
    try {
      await agentosApi.createDecision({
        ...decisionForm,
        confidence: Number(decisionForm.confidence),
        risk_plan: { require_human_review: true },
        position_plan: { mode: 'research_only' },
      })
      toast.success('Decision recorded')
      await refresh()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }, [decisionForm, refresh])

  const runReview = useCallback(async () => {
    setBusy('review')
    try {
      await agentosApi.runWeeklyReview()
      toast.success('Weekly review generated')
      await refresh()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }, [refresh])

  const approveLesson = useCallback(async (id: string) => {
    setBusy(id)
    try {
      await agentosApi.approveLesson(id)
      toast.success('Lesson approved')
      await refresh()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }, [refresh])

  const createHypothesis = useCallback(async () => {
    if (!hypothesisForm.name.trim() || !hypothesisForm.hypothesis.trim()) {
      toast.error('Name and hypothesis are required')
      return
    }
    setBusy('hypothesis')
    try {
      const result = await agentosApi.createHypothesis({
        ...hypothesisForm,
        asset_universe: splitSymbols(hypothesisForm.asset_universe),
        frequency: 'daily',
      })
      setSelectedHypothesisId(result.hypothesis.id)
      toast.success('Hypothesis created')
      await refresh()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }, [hypothesisForm, refresh])

  const recordValidation = useCallback(async () => {
    if (!validationForm.symbol.trim()) {
      toast.error('Symbol is required')
      return
    }
    setBusy('validation')
    try {
      await agentosApi.runValidation({
        symbol: validationForm.symbol,
        strategy: 'fundamental_validation',
        params: {
          conclusion: validationForm.conclusion || 'observe',
          evidence: splitLines(validationForm.evidence),
          risks: splitLines(validationForm.risks),
          notes: validationForm.notes,
        },
        hypothesis_id: selectedHypothesisId || null,
      })
      toast.success('Fundamental validation recorded')
      await refresh()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(null)
    }
  }, [refresh, selectedHypothesisId, validationForm])

  return {
    state: {
      loading,
      busy,
      health,
      briefs,
      memos,
      decisions,
      lessons,
      memory,
      hypotheses,
      validations,
      reportHits,
      watchlist,
      researchSymbol,
      reportQuery,
      decisionForm,
      hypothesisForm,
      validationForm,
      selectedHypothesisId,
    },
    actions: {
      refresh,
      runBrief,
      runResearch,
      searchReports,
      recordDecision,
      runReview,
      approveLesson,
      createHypothesis,
      recordValidation,
      setWatchlist,
      setResearchSymbol,
      setReportQuery,
      setDecisionForm,
      setHypothesisForm,
      setValidationForm,
      setSelectedHypothesisId,
    },
  }
}

function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}
