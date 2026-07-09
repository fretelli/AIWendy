'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PositionCard } from './PositionCard';
import { PnLChart } from './PnLChart';
import { Loader2 } from 'lucide-react';
import {
  getNumber,
  getString,
  isPnLData,
  isPositionData,
  type JsonObject,
} from './tool-call-types';

interface ToolCallCardProps {
  name: string;
  args: JsonObject;
  result?: JsonObject;
}

const TOOL_LABELS: Record<string, string> = {
  get_positions: 'Positions',
  get_pnl: 'PnL',
  query_trades: 'Trade History',
  analyze_performance: 'Performance',
  detect_patterns: 'Patterns',
  run_daily_brief: 'Daily Brief',
  deep_research: 'Fundamental Research',
  place_order: 'Order',
  cancel_order: 'Cancel Order',
  search_knowledge: 'Knowledge',
  manage_journal: 'Journal',
  update_settings: 'Settings',
  query_research_reports: 'Research Reports',
  query_tushare_data: 'Tushare Data',
  record_fundamental_validation: 'Fundamental Validation',
};

export function ToolCallCard({ name, args, result }: ToolCallCardProps) {
  const label = TOOL_LABELS[name] || name;

  if (!result) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-1">
        <Loader2 className="h-3 w-3 animate-spin" />
        Executing {label}...
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
          {getString(result.error, 'Tool execution failed')}
        </CardContent>
      </Card>
    );
  }

  // Specialized renderers
  if (name === 'get_positions' && Array.isArray(result.positions)) {
    const positions = result.positions.filter(isPositionData);
    return <PositionCard positions={positions} totalPnl={getNumber(result.total_unrealized_pnl)} />;
  }

  if (name === 'get_pnl' && isPnLData(result)) {
    return <PnLChart data={result} />;
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
