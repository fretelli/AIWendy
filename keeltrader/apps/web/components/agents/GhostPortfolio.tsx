'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { GhostTrade, PortfolioSummary } from '@/lib/types/agents'

interface GhostPortfolioProps {
  trades: GhostTrade[]
  portfolio: PortfolioSummary | null
  loading: boolean
}

function PnlCell({ value }: { value: number }) {
  const color = value > 0 ? 'text-green-600 dark:text-green-400' : value < 0 ? 'text-red-600 dark:text-red-400' : ''
  const prefix = value > 0 ? '+' : ''
  return <span className={`font-mono ${color}`}>{prefix}{value.toFixed(4)}</span>
}

export function GhostPortfolio({ trades, portfolio, loading }: GhostPortfolioProps) {
  if (loading && !portfolio) {
    return <div className="text-sm text-muted-foreground">Loading...</div>
  }

  const openTrades = trades.filter(t => t.status === 'open')
  const closedTrades = trades.filter(t => t.status === 'closed')

  return (
    <div className="space-y-6">
      {/* Summary Row */}
      {portfolio && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{portfolio.open_positions}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Unrealized P&L</CardTitle>
            </CardHeader>
            <CardContent>
              <PnlCell value={portfolio.total_unrealized_pnl} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Realized P&L</CardTitle>
            </CardHeader>
            <CardContent>
              <PnlCell value={portfolio.total_realized_pnl} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{portfolio.win_rate}%</p>
              <p className="text-xs text-muted-foreground">
                {portfolio.win_count}W / {portfolio.loss_count}L ({portfolio.closed_trades} total)
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Open Trades */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Open Positions ({openTrades.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {openTrades.length === 0 ? (
            <p className="text-sm text-muted-foreground">No open positions</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Side</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Entry Price</TableHead>
                  <TableHead>SL / TP</TableHead>
                  <TableHead>Unrealized P&L</TableHead>
                  <TableHead>Agent</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {openTrades.map((trade) => (
                  <TableRow key={trade.id}>
                    <TableCell className="font-medium">{trade.symbol}</TableCell>
                    <TableCell>
                      <Badge variant={trade.side === 'buy' ? 'default' : 'destructive'}>
                        {trade.side.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono">{parseFloat(trade.amount).toFixed(4)}</TableCell>
                    <TableCell className="font-mono">${parseFloat(trade.entry_price).toLocaleString()}</TableCell>
                    <TableCell className="text-xs">
                      {parseFloat(trade.stop_loss) > 0 && <span className="text-red-500">SL: ${parseFloat(trade.stop_loss).toLocaleString()}</span>}
                      {parseFloat(trade.stop_loss) > 0 && parseFloat(trade.take_profit) > 0 && ' / '}
                      {parseFloat(trade.take_profit) > 0 && <span className="text-green-500">TP: ${parseFloat(trade.take_profit).toLocaleString()}</span>}
                      {parseFloat(trade.stop_loss) === 0 && parseFloat(trade.take_profit) === 0 && '-'}
                    </TableCell>
                    <TableCell><PnlCell value={parseFloat(trade.unrealized_pnl)} /></TableCell>
                    <TableCell className="text-xs text-muted-foreground">{trade.agent_id}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Closed Trades */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Closed Trades ({closedTrades.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {closedTrades.length === 0 ? (
            <p className="text-sm text-muted-foreground">No closed trades</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Side</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Entry</TableHead>
                  <TableHead>Exit</TableHead>
                  <TableHead>Realized P&L</TableHead>
                  <TableHead>Agent</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {closedTrades.map((trade) => (
                  <TableRow key={trade.id}>
                    <TableCell className="font-medium">{trade.symbol}</TableCell>
                    <TableCell>
                      <Badge variant={trade.side === 'buy' ? 'default' : 'destructive'}>
                        {trade.side.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono">{parseFloat(trade.amount).toFixed(4)}</TableCell>
                    <TableCell className="font-mono">${parseFloat(trade.entry_price).toLocaleString()}</TableCell>
                    <TableCell className="font-mono">${trade.exit_price ? parseFloat(trade.exit_price).toLocaleString() : '-'}</TableCell>
                    <TableCell><PnlCell value={parseFloat(trade.realized_pnl)} /></TableCell>
                    <TableCell className="text-xs text-muted-foreground">{trade.agent_id}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
