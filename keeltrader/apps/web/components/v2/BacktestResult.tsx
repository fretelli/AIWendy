'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

interface BacktestData {
  symbol: string;
  strategy: string;
  params?: Record<string, any>;
  period_days: number;
  stats: {
    total_trades: number;
    wins: number;
    losses: number;
    win_rate: number;
    total_return_pct: number;
    avg_win_pct: number;
    avg_loss_pct: number;
    max_drawdown_pct: number;
    profit_factor: number;
    sharpe_ratio: number;
  };
  equity_curve?: number[];
  trades?: any[];
}

interface BacktestResultProps {
  data: BacktestData;
}

export function BacktestResult({ data }: BacktestResultProps) {
  const { stats, equity_curve } = data;
  const isPositive = stats.total_return_pct > 0;

  const equityData = equity_curve?.map((value, index) => ({
    index,
    value,
  }));

  return (
    <Card>
      <CardHeader className="py-2 px-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm">📈 Backtest Result</CardTitle>
            <Badge variant="secondary" className="text-xs">{data.strategy}</Badge>
          </div>
          <span className={cn(
            'text-lg font-mono font-bold',
            isPositive ? 'text-green-600' : 'text-red-600'
          )}>
            {isPositive ? '+' : ''}{stats.total_return_pct.toFixed(2)}%
          </span>
        </div>
        <div className="text-xs text-muted-foreground">
          {data.symbol} · {data.period_days}d · {stats.total_trades} trades
        </div>
      </CardHeader>
      <CardContent className="px-3 pb-2 space-y-2">
        {/* Stats grid */}
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="text-center p-1 rounded bg-muted">
            <div className="text-muted-foreground">Win Rate</div>
            <div className="font-bold">{stats.win_rate}%</div>
          </div>
          <div className="text-center p-1 rounded bg-muted">
            <div className="text-muted-foreground">P/F Ratio</div>
            <div className="font-bold">{stats.profit_factor}</div>
          </div>
          <div className="text-center p-1 rounded bg-muted">
            <div className="text-muted-foreground">Max DD</div>
            <div className="font-bold text-red-600">-{stats.max_drawdown_pct}%</div>
          </div>
          <div className="text-center p-1 rounded bg-muted">
            <div className="text-muted-foreground">Avg Win</div>
            <div className="font-bold text-green-600">+{stats.avg_win_pct}%</div>
          </div>
          <div className="text-center p-1 rounded bg-muted">
            <div className="text-muted-foreground">Avg Loss</div>
            <div className="font-bold text-red-600">{stats.avg_loss_pct}%</div>
          </div>
          <div className="text-center p-1 rounded bg-muted">
            <div className="text-muted-foreground">Sharpe</div>
            <div className="font-bold">{stats.sharpe_ratio}</div>
          </div>
        </div>

        {/* Equity curve */}
        {equityData && equityData.length > 0 && (
          <div className="h-[100px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={equityData}>
                <XAxis dataKey="index" hide />
                <YAxis tick={{ fontSize: 10 }} width={40} domain={['auto', 'auto']} />
                <Tooltip
                  formatter={(value: number) => [`${value.toFixed(2)}%`, 'Equity']}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={isPositive ? '#16a34a' : '#dc2626'}
                  strokeWidth={1.5}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
