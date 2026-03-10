'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

interface PnLData {
  period: string;
  total_pnl: number;
  wins: number;
  losses: number;
  trade_count: number;
  daily_pnl: { date: string; pnl: number }[];
}

interface PnLChartProps {
  data: PnLData;
}

export function PnLChart({ data }: PnLChartProps) {
  const hasChart = data.daily_pnl && data.daily_pnl.length > 0;

  const periodLabel: Record<string, string> = {
    today: '今日',
    week: '本周',
    month: '本月',
    all: '全部',
  };

  return (
    <Card>
      <CardHeader className="py-2 px-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">
            💰 {periodLabel[data.period] || data.period}盈亏
          </CardTitle>
          <span className={cn(
            'text-lg font-mono font-bold',
            data.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'
          )}>
            ${data.total_pnl >= 0 ? '+' : ''}{data.total_pnl.toFixed(2)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="px-3 pb-2">
        <div className="flex gap-4 text-sm mb-2">
          <span>交易 {data.trade_count} 笔</span>
          <span className="text-green-600">赢 {data.wins}</span>
          <span className="text-red-600">亏 {data.losses}</span>
          {data.trade_count > 0 && (
            <span>
              胜率 {((data.wins / data.trade_count) * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {hasChart && (
          <div className="h-[120px] mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.daily_pnl}>
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis tick={{ fontSize: 10 }} width={50} />
                <Tooltip
                  formatter={(value: number) => [`$${value.toFixed(2)}`, '盈亏']}
                  labelFormatter={(label: string) => label}
                />
                <Bar dataKey="pnl">
                  {data.daily_pnl.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={entry.pnl >= 0 ? '#16a34a' : '#dc2626'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
