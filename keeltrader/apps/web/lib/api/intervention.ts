/**
 * Intervention API client
 */

import { API_V1_PREFIX } from "@/lib/config"

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
    const token = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(`${API_V1_PREFIX}/intervention/check-trade`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
      },
      body: JSON.stringify(tradeData),
    })

    if (!response.ok) {
      throw new Error("Failed to check trade")
    }

    return response.json()
  },

  async getChecklists(): Promise<Checklist[]> {
    const token = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(`${API_V1_PREFIX}/intervention/checklists`, {
      headers: {
        Authorization: token ? `Bearer ${token}` : "",
      },
    })

    if (!response.ok) {
      throw new Error("Failed to fetch checklists")
    }

    return response.json()
  },

  async createChecklist(
    name: string,
    items: ChecklistItem[],
    description?: string,
    isRequired: boolean = false
  ): Promise<Checklist> {
    const token = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(`${API_V1_PREFIX}/intervention/checklists`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
      },
      body: JSON.stringify({
        name,
        description,
        items,
        is_required: isRequired,
      }),
    })

    if (!response.ok) {
      throw new Error("Failed to create checklist")
    }

    return response.json()
  },

  async completeChecklist(
    checklistId: string,
    responses: Record<string, any>
  ): Promise<void> {
    const token = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(
      `${API_V1_PREFIX}/intervention/checklists/complete`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          checklist_id: checklistId,
          responses,
        }),
      }
    )

    if (!response.ok) {
      throw new Error("Failed to complete checklist")
    }
  },

  async startSession(
    maxDailyLossLimit?: number,
    maxTradesPerDay?: number
  ): Promise<TradingSession> {
    const token = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(`${API_V1_PREFIX}/intervention/session/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
      },
      body: JSON.stringify({
        max_daily_loss_limit: maxDailyLossLimit,
        max_trades_per_day: maxTradesPerDay,
      }),
    })

    if (!response.ok) {
      throw new Error("Failed to start trading session")
    }

    return response.json()
  },

  async acknowledgeIntervention(
    interventionId: string,
    userProceeded: boolean = false,
    userNotes?: string
  ): Promise<void> {
    const token = localStorage.getItem("keeltrader_access_token")
    const response = await fetch(
      `${API_V1_PREFIX}/intervention/interventions/${interventionId}/acknowledge`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          user_proceeded: userProceeded,
          user_notes: userNotes,
        }),
      }
    )

    if (!response.ok) {
      throw new Error("Failed to acknowledge intervention")
    }
  },
}
