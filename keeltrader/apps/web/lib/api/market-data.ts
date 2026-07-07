/**
 * Market Data API Client
 */

import { apiJson } from '@/lib/api/client'

const API_BASE_URL = '/market-data'

export interface PriceData {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface RealTimePrice {
  symbol: string
  price: number
  change: number
  change_percent: number
  timestamp: string
  volume: number
}

export interface IndicatorData {
  time: string
  value: number
}

export interface SymbolSearchResult {
  symbol: string
  name: string
  type: string
}

export const marketDataApi = {
  /**
   * Get historical price data
   */
  async getHistoricalData(
    symbol: string,
    interval: string = '1day',
    outputsize: number = 60,
    startDate?: string,
    endDate?: string
  ): Promise<PriceData[]> {
    const params = new URLSearchParams({
      interval,
      outputsize: outputsize.toString()
    })

    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)

    return apiJson<PriceData[]>(`${API_BASE_URL}/historical/${symbol}?${params}`)
  },

  /**
   * Get real-time price
   */
  async getRealTimePrice(symbol: string): Promise<RealTimePrice> {
    return apiJson<RealTimePrice>(`${API_BASE_URL}/real-time/${symbol}`)
  },

  /**
   * Get technical indicators
   */
  async getTechnicalIndicators(
    symbol: string,
    indicator: 'sma' | 'ema' | 'rsi' | 'macd' | 'bbands',
    interval: string = '1day',
    period: number = 20
  ): Promise<IndicatorData[]> {
    const params = new URLSearchParams({
      interval,
      period: period.toString()
    })

    return apiJson<IndicatorData[]>(`${API_BASE_URL}/indicators/${symbol}/${indicator}?${params}`)
  },

  /**
   * Search for symbols
   */
  async searchSymbols(query: string): Promise<SymbolSearchResult[]> {
    const params = new URLSearchParams({ query })

    return apiJson<SymbolSearchResult[]>(`${API_BASE_URL}/symbols/search?${params}`)
  },
}
