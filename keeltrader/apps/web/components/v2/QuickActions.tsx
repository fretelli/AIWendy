'use client';

import { Button } from '@/components/ui/button';
import {
  Wallet,
  TrendingUp,
  BarChart3,
  LineChart,
  RefreshCw,
  MoreHorizontal,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface QuickActionsProps {
  onAction: (action: string, params?: Record<string, any>) => void;
  disabled?: boolean;
}

const PRIMARY_ACTIONS = [
  { action: 'get_positions', label: '查持仓', icon: Wallet },
  { action: 'get_pnl', label: '今日盈亏', icon: TrendingUp, params: { period: 'today' } },
  { action: 'analyze_performance', label: '交易分析', icon: BarChart3, params: { days: 7 } },
];

const MORE_ACTIONS = [
  { action: 'get_pnl', label: '本周盈亏', params: { period: 'week' } },
  { action: 'get_pnl', label: '本月盈亏', params: { period: 'month' } },
  { action: 'detect_patterns', label: '行为模式检测', params: { days: 14 } },
  { action: 'analyze_performance', label: '30天分析', params: { days: 30 } },
];

export function QuickActions({ onAction, disabled }: QuickActionsProps) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b overflow-x-auto">
      {PRIMARY_ACTIONS.map(({ action, label, icon: Icon, params }) => (
        <Button
          key={`${action}-${label}`}
          variant="outline"
          size="sm"
          className="shrink-0 gap-1.5"
          onClick={() => onAction(action, params)}
          disabled={disabled}
        >
          <Icon className="h-3.5 w-3.5" />
          {label}
        </Button>
      ))}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="shrink-0 gap-1.5" disabled={disabled}>
            <MoreHorizontal className="h-3.5 w-3.5" />
            更多
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {MORE_ACTIONS.map(({ action, label, params }, i) => (
            <DropdownMenuItem
              key={i}
              onClick={() => onAction(action, params)}
            >
              {label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
