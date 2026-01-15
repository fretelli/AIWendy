/**
 * Market Data WebSocket Client
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
      console.log('WebSocket already connected')
      return
    }

    // Get WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/market-data/ws/${this.symbol}`

    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log(`Connected to market data stream for ${this.symbol}`)
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
      console.log('WebSocket closed')
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

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`)

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
  if (typeof window === 'undefined') {
    // Server-side rendering
    return {
      price: null,
      isConnected: false,
      error: null,
    }
  }

  const [price, setPrice] = React.useState<PriceUpdate | null>(null)
  const [isConnected, setIsConnected] = React.useState(false)
  const [error, setError] = React.useState<Event | null>(null)
  const wsRef = React.useRef<MarketDataWebSocket | null>(null)

  React.useEffect(() => {
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
  }, [symbol])

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
