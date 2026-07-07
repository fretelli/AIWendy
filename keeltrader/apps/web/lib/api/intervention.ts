/**
 * Intervention API client
 */

import { apiFetch, apiJson } from "@/lib/api/client"

export interface Checklist {
  id: string
  name: string
  description: string
  items: ChecklistItem[]
  is_required: boolean
  is_active: boolean
  created_at: string
}

export interface ChecklistItem {
  id: string
  type: string
  question: string
  required: boolean
}

export interface TradingSession {
  id: string
  is_active: boolean
  trades_count: number
  session_pnl: number
  max_daily_loss_limit: number | null
  max_trades_per_day: number | null
  started_at: string
}

export interface CheckTradeRequest {
  symbol: string
  direction: string
  position_size: number
  entry_price: number
}

export interface CheckTradeResponse {
  allowed: boolean
  action: string
  reason: string | null
  message: string
  intervention_id: string | null
  checklist_required?: boolean
}

export const interventionApi = {
  async checkTrade(tradeData: CheckTradeRequest): Promise<CheckTradeResponse> {
    return apiJson<CheckTradeResponse>("/intervention/check-trade", {
      method: "POST",
      body: tradeData,
    })
  },

  async getChecklists(): Promise<Checklist[]> {
    return apiJson<Checklist[]>("/intervention/checklists")
  },

  async createChecklist(
    name: string,
    items: ChecklistItem[],
    description?: string,
    isRequired: boolean = false
  ): Promise<Checklist> {
    return apiJson<Checklist>("/intervention/checklists", {
      method: "POST",
      body: {
        name,
        description,
        items,
        is_required: isRequired,
      },
    })
  },

  async completeChecklist(
    checklistId: string,
    responses: Record<string, any>
  ): Promise<void> {
    const response = await apiFetch("/intervention/checklists/complete", {
      method: "POST",
      body: {
        checklist_id: checklistId,
        responses,
      },
    })

    if (!response.ok) {
      throw new Error("Failed to complete checklist")
    }
  },

  async startSession(
    maxDailyLossLimit?: number,
    maxTradesPerDay?: number
  ): Promise<TradingSession> {
    return apiJson<TradingSession>("/intervention/session/start", {
      method: "POST",
      body: {
        max_daily_loss_limit: maxDailyLossLimit,
        max_trades_per_day: maxTradesPerDay,
      },
    })
  },

  async acknowledgeIntervention(
    interventionId: string,
    userProceeded: boolean = false,
    userNotes?: string
  ): Promise<void> {
    const response = await apiFetch(`/intervention/interventions/${interventionId}/acknowledge`, {
      method: "POST",
      body: {
        user_proceeded: userProceeded,
        user_notes: userNotes,
      },
    })

    if (!response.ok) {
      throw new Error("Failed to acknowledge intervention")
    }
  },
}
