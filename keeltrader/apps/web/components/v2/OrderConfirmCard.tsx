'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface OrderConfirmCardProps {
  order: {
    symbol: string;
    side: string;
    amount: number;
    order_type: string;
    price?: number;
    stop_loss?: number;
    take_profit?: number;
    estimated_value_usd?: number;
  };
  message: string;
  onConfirm: (orderData: Record<string, any>) => void;
}

export function OrderConfirmCard({ order, message, onConfirm }: OrderConfirmCardProps) {
  const [confirmed, setConfirmed] = useState(false);
  const [skipped, setSkipped] = useState(false);

  if (skipped) {
    return (
      <Card className="border-yellow-500/50">
        <CardContent className="py-2 px-3 text-sm text-muted-foreground">
          ⏭️ 已跳过此交易
        </CardContent>
      </Card>
    );
  }

  if (confirmed) {
    return (
      <Card className="border-green-500/50">
        <CardContent className="py-2 px-3 text-sm text-green-600">
          ✅ 已确认执行
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/50">
      <CardHeader className="py-2 px-3">
        <div className="flex items-center gap-2">
          <CardTitle className="text-sm">⚡ 交易确认</CardTitle>
          <Badge variant={order.side === 'buy' ? 'default' : 'destructive'}>
            {order.side === 'buy' ? '买入' : '卖出'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="px-3 pb-2 space-y-2">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <div className="text-muted-foreground">交易对</div>
          <div className="font-medium">{order.symbol}</div>

          <div className="text-muted-foreground">数量</div>
          <div className="font-mono">{order.amount}</div>

          <div className="text-muted-foreground">类型</div>
          <div>{order.order_type === 'market' ? '市价' : '限价'}</div>

          {order.price && (
            <>
              <div className="text-muted-foreground">价格</div>
              <div className="font-mono">${order.price}</div>
            </>
          )}

          {order.stop_loss && (
            <>
              <div className="text-muted-foreground">止损</div>
              <div className="font-mono text-red-600">${order.stop_loss}</div>
            </>
          )}

          {order.take_profit && (
            <>
              <div className="text-muted-foreground">止盈</div>
              <div className="font-mono text-green-600">${order.take_profit}</div>
            </>
          )}

          {order.estimated_value_usd && (
            <>
              <div className="text-muted-foreground">预估金额</div>
              <div className="font-mono">${order.estimated_value_usd.toFixed(2)}</div>
            </>
          )}
        </div>

        <div className="flex gap-2 pt-1">
          <Button
            size="sm"
            onClick={() => {
              setConfirmed(true);
              onConfirm(order);
            }}
          >
            ✅ 执行
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSkipped(true)}
          >
            ⏭️ 跳过
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
