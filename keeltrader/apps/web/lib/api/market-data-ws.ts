/**
 * Market Data WebSocket Client
 *
 * WebSocket traffic is not handled by the Next.js HTTP API proxy. Deployments
 * that use this client must explicitly expose a protected WS upstream and set
 * NEXT_PUBLIC_MARKET_DATA_WS_URL, for example:
 * wss://example.com/api/v1/market-data/ws
 */

interface PriceUpdate {
  type: 'price_update'
  symbol: string
  price: number
  timestamp: string
}

interface MarketDataWSOptions {
  onPriceUpdate?: (data: PriceUpdate) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnect?: boolean
  reconnectDelay?: number
  maxReconnectDelay?: number
}

function debugMarketDataWs(message: string): void {
  if (process.env.NEXT_PUBLIC_MARKET_DATA_WS_DEBUG === '1') {
    console.debug(message)
  }
}

export class MarketDataWebSocket {
  private ws: WebSocket | null = null
  private symbol: string
  private options: Required<MarketDataWSOptions>
  private reconnectAttempts = 0
  private shouldReconnect = true
  private reconnectTimeout: NodeJS.Timeout | null = null

  constructor(symbol: string, options: MarketDataWSOptions = {}) {
    this.symbol = symbol
    this.options = {
      onPriceUpdate: options.onPriceUpdate || (() => {}),
      onConnect: options.onConnect || (() => {}),
      onDisconnect: options.onDisconnect || (() => {}),
      onError: options.onError || (() => {}),
      reconnect: options.reconnect !== false,
      reconnectDelay: options.reconnectDelay || 1000,
      maxReconnectDelay: options.maxReconnectDelay || 30000,
    }
  }

  /**
   * Connect to the WebSocket
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      debugMarketDataWs('WebSocket already connected')
      return
    }

    const configuredBaseUrl = process.env.NEXT_PUBLIC_MARKET_DATA_WS_URL?.replace(/\/+$/, '')
    if (!configuredBaseUrl) {
      console.warn('Market data WebSocket URL is not configured')
      this.options.onDisconnect()
      return
    }

    const wsUrl = `${configuredBaseUrl}/${encodeURIComponent(this.symbol)}`

    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      debugMarketDataWs(`Connected to market data stream for ${this.symbol}`)
      this.reconnectAttempts = 0
      this.options.onConnect()
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'price_update') {
          this.options.onPriceUpdate(data)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.options.onError(error)
    }

    this.ws.onclose = () => {
      debugMarketDataWs('WebSocket closed')
      this.options.onDisconnect()
      this.ws = null

      // Attempt to reconnect if enabled
      if (this.shouldReconnect && this.options.reconnect) {
        this.scheduleReconnect()
      }
    }
  }

  /**
   * Schedule a reconnection attempt with exponential backoff
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }

    const delay = Math.min(
      this.options.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.options.maxReconnectDelay
    )

    debugMarketDataWs(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`)

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, delay)
  }

  /**
   * Subscribe to a new symbol
   */
  subscribe(symbol: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        symbol,
      }))
    } else {
      console.warn('Cannot subscribe: WebSocket not connected')
    }
  }

  /**
   * Unsubscribe from a symbol
   */
  unsubscribe(symbol: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'unsubscribe',
        symbol,
      }))
    } else {
      console.warn('Cannot unsubscribe: WebSocket not connected')
    }
  }

  /**
   * Disconnect from the WebSocket
   */
  disconnect(): void {
    this.shouldReconnect = false

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * Get current symbol
   */
  getSymbol(): string {
    return this.symbol
  }
}

/**
 * React Hook for Market Data WebSocket
 */
export function useMarketDataWebSocket(
  symbol: string,
  options: MarketDataWSOptions = {}
) {
  const [price, setPrice] = React.useState<PriceUpdate | null>(null)
  const [isConnected, setIsConnected] = React.useState(false)
  const [error, setError] = React.useState<Event | null>(null)
  const wsRef = React.useRef<MarketDataWebSocket | null>(null)

  React.useEffect(() => {
    if (typeof window === 'undefined') {
      // Server-side rendering - skip WebSocket connection
      return
    }

    // Create WebSocket instance
    wsRef.current = new MarketDataWebSocket(symbol, {
      ...options,
      onPriceUpdate: (data) => {
        setPrice(data)
        options.onPriceUpdate?.(data)
      },
      onConnect: () => {
        setIsConnected(true)
        setError(null)
        options.onConnect?.()
      },
      onDisconnect: () => {
        setIsConnected(false)
        options.onDisconnect?.()
      },
      onError: (err) => {
        setError(err)
        options.onError?.(err)
      },
    })

    // Connect
    wsRef.current.connect()

    // Cleanup
    return () => {
      wsRef.current?.disconnect()
    }
  }, [symbol, options])

  return {
    price,
    isConnected,
    error,
    subscribe: (newSymbol: string) => wsRef.current?.subscribe(newSymbol),
    unsubscribe: (sym: string) => wsRef.current?.unsubscribe(sym),
  }
}

// Re-export React for the hook
import * as React from 'react'
