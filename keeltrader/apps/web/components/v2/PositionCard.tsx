'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface Position {
  exchange: string;
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  leverage: number;
  error?: string;
}

interface PositionCardProps {
  positions: Position[];
  totalPnl: number;
}

export function PositionCard({ positions, totalPnl }: PositionCardProps) {
  const validPositions = positions.filter(p => !p.error);

  return (
    <Card>
      <CardHeader className="py-2 px-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">📊 持仓概况</CardTitle>
          <span className={cn(
            'text-sm font-mono font-bold',
            totalPnl >= 0 ? 'text-green-600' : 'text-red-600'
          )}>
            ${totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="px-3 pb-2">
        {validPositions.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无持仓</p>
        ) : (
          <div className="space-y-2">
            {validPositions.map((p, i) => (
              <div key={i} className="flex items-center justify-between text-sm border-b pb-1 last:border-0">
                <div className="flex items-center gap-2">
                  <Badge variant={p.side === 'long' ? 'default' : 'destructive'} className="text-xs">
                    {p.side === 'long' ? '多' : '空'}
                  </Badge>
                  <span className="font-medium">{p.symbol}</span>
                  <span className="text-xs text-muted-foreground">{p.exchange}</span>
                </div>
                <div className="text-right">
                  <div className="font-mono text-xs">
                    {p.size} @ {p.entry_price}
                  </div>
                  <div className={cn(
                    'font-mono text-xs font-bold',
                    p.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                  )}>
                    ${p.unrealized_pnl >= 0 ? '+' : ''}{p.unrealized_pnl.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
