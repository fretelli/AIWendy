'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PositionCard } from './PositionCard';
import { PnLChart } from './PnLChart';
import { BacktestResult } from './BacktestResult';
import { Loader2 } from 'lucide-react';

interface ToolCallCardProps {
  name: string;
  args: Record<string, any>;
  result?: Record<string, any>;
}

const TOOL_LABELS: Record<string, string> = {
  get_positions: '持仓查询',
  get_pnl: '盈亏查询',
  query_trades: '交易记录',
  analyze_performance: '交易分析',
  detect_patterns: '行为模式',
  get_market_data: '行情数据',
  analyze_market: '市场分析',
  place_order: '下单',
  cancel_order: '撤单',
  search_knowledge: '知识搜索',
  manage_journal: '交易日志',
  update_settings: '设置更新',
  generate_chart: '图表',
  backtest_strategy: '回测',
  replay_my_trades: '交易回放',
};

export function ToolCallCard({ name, args, result }: ToolCallCardProps) {
  const label = TOOL_LABELS[name] || name;

  if (!result) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-1">
        <Loader2 className="h-3 w-3 animate-spin" />
        正在执行 {label}...
      </div>
    );
  }

  if (result.error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader className="py-2 px-3">
          <div className="flex items-center gap-2">
            <Badge variant="destructive" className="text-xs">{label}</Badge>
          </div>
        </CardHeader>
        <CardContent className="px-3 pb-2 text-sm text-destructive">
          {result.error}
        </CardContent>
      </Card>
    );
  }

  // Specialized renderers
  if (name === 'get_positions' && result.positions) {
    return <PositionCard positions={result.positions} totalPnl={result.total_unrealized_pnl} />;
  }

  if (name === 'get_pnl' && result.daily_pnl) {
    return <PnLChart data={result} />;
  }

  if (name === 'backtest_strategy' && result.stats) {
    return <BacktestResult data={result} />;
  }

  // Generic result display
  return (
    <Card>
      <CardHeader className="py-2 px-3">
        <Badge variant="secondary" className="text-xs w-fit">{label}</Badge>
      </CardHeader>
      <CardContent className="px-3 pb-2">
        <pre className="text-xs whitespace-pre-wrap overflow-x-auto max-h-[300px] overflow-y-auto">
          {JSON.stringify(result, null, 2)}
        </pre>
      </CardContent>
    </Card>
  );
}
