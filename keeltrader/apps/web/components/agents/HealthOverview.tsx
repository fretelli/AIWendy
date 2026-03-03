'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { HealthResponse, CachedPrices } from '@/lib/types/agents'

interface HealthOverviewProps {
  health: HealthResponse | null
  prices: CachedPrices | null
  loading: boolean
}

function StatusBadge({ status }: { status: string }) {
  const variant = status === 'running' || status === 'active' || status === 'healthy'
    ? 'default'
    : status === 'degraded'
      ? 'secondary'
      : 'outline'
  return <Badge variant={variant}>{status}</Badge>
}

export function HealthOverview({ health, prices, loading }: HealthOverviewProps) {
  if (loading && !health) {
    return <div className="text-sm text-muted-foreground">Loading...</div>
  }

  const services = health?.services

  return (
    <div className="space-y-6">
      {/* Service Status Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Event Engine</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge status={services?.event_engine?.status || 'unknown'} />
            {services?.event_engine?.uptime && (
              <p className="mt-1 text-xs text-muted-foreground">
                Uptime: {services.event_engine.uptime}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Market Streamer</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge status={services?.market_streamer?.status || 'unknown'} />
            {services?.market_streamer?.symbols && (
              <p className="mt-1 text-xs text-muted-foreground">
                Symbols: {services.market_streamer.symbols}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Circuit Breaker</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={services?.circuit_breaker?.active ? 'destructive' : 'default'}>
              {services?.circuit_breaker?.active ? 'ACTIVE' : 'inactive'}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Event Bus</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge status={services?.event_bus?.status || 'unknown'} />
            {services?.event_bus?.length !== undefined && (
              <p className="mt-1 text-xs text-muted-foreground">
                Events: {services.event_bus.length}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Overall Status */}
      {health && (
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Overall:</span>
          <StatusBadge status={health.status} />
          {services?.market_data && (
            <span className="text-xs text-muted-foreground">
              | {services.market_data.cached_symbols} cached symbols
            </span>
          )}
        </div>
      )}

      {/* Cached Prices Grid */}
      {prices && Object.keys(prices).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Real-time Prices</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {Object.entries(prices).map(([symbol, price]) => (
                <div key={symbol} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span className="text-sm font-medium">{symbol}</span>
                  <span className="text-sm font-mono">${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
