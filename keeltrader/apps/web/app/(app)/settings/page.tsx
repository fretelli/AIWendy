'use client';

import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('keeltrader_access_token') || localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface Exchange {
  id: string;
  exchange: string;
  trading_mode: string;
  is_testnet: boolean;
  last_sync: string | null;
}

export default function SettingsPage() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [riskSettings, setRiskSettings] = useState({
    max_order_value_usd: 5000,
    max_daily_loss_usd: 500,
    max_positions: 5,
    require_confirmation: true,
  });
  const [pushSettings, setPushSettings] = useState({
    push_morning_report: true,
    push_evening_report: true,
    push_trade_alerts: true,
    push_risk_alerts: true,
  });

  // New exchange form
  const [newExchange, setNewExchange] = useState({
    exchange: 'okx',
    api_key: '',
    api_secret: '',
    passphrase: '',
    trading_mode: 'swap',
  });

  const fetchData = useCallback(async () => {
    try {
      const [exResp, riskResp, pushResp] = await Promise.all([
        fetch(`${API_BASE}/api/v1/settings/exchanges`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/api/v1/settings/risk`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/api/v1/settings/push`, { headers: getAuthHeaders() }),
      ]);

      if (exResp.ok) {
        const data = await exResp.json();
        setExchanges(data.exchanges || []);
      }
      if (riskResp.ok) setRiskSettings(await riskResp.json());
      if (pushResp.ok) setPushSettings(await pushResp.json());
    } catch (e) {
      console.error('Failed to load settings', e);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const addExchange = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/v1/settings/exchanges`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(newExchange),
      });
      const data = await resp.json();
      if (resp.ok) {
        toast.success(data.message || 'Connected successfully');
        setNewExchange({ exchange: 'okx', api_key: '', api_secret: '', passphrase: '', trading_mode: 'swap' });
        fetchData();
      } else {
        toast.error(data.detail || 'Connection failed');
      }
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const removeExchange = async (id: string) => {
    const resp = await fetch(`${API_BASE}/api/v1/settings/exchanges/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (resp.ok) {
      toast.success('Disconnected');
      fetchData();
    }
  };

  const saveRiskSettings = async () => {
    const resp = await fetch(`${API_BASE}/api/v1/settings/risk`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(riskSettings),
    });
    if (resp.ok) toast.success('Risk settings saved');
  };

  const savePushSettings = async () => {
    const resp = await fetch(`${API_BASE}/api/v1/settings/push`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(pushSettings),
    });
    if (resp.ok) toast.success('Push settings saved');
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Exchange connections */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Exchange Connections</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {exchanges.length > 0 && (
            <div className="space-y-2">
              {exchanges.map(ex => (
                <div key={ex.id} className="flex items-center justify-between p-2 border rounded">
                  <div className="flex items-center gap-2">
                    <Badge>{ex.exchange.toUpperCase()}</Badge>
                    <span className="text-sm">{ex.trading_mode}</span>
                    {ex.is_testnet && <Badge variant="outline">Testnet</Badge>}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => removeExchange(ex.id)}>
                    Disconnect
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-3 border-t pt-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Exchange</Label>
                <select
                  className="w-full rounded border px-3 py-2 text-sm"
                  value={newExchange.exchange}
                  onChange={e => setNewExchange(p => ({ ...p, exchange: e.target.value }))}
                >
                  <option value="okx">OKX</option>
                  <option value="bybit">Bybit</option>
                  <option value="coinbase">Coinbase</option>
                  <option value="kraken">Kraken</option>
                </select>
              </div>
              <div>
                <Label>Trading Mode</Label>
                <select
                  className="w-full rounded border px-3 py-2 text-sm"
                  value={newExchange.trading_mode}
                  onChange={e => setNewExchange(p => ({ ...p, trading_mode: e.target.value }))}
                >
                  <option value="swap">Futures (swap)</option>
                  <option value="spot">Spot</option>
                </select>
              </div>
            </div>
            <div>
              <Label>API Key</Label>
              <Input
                type="password"
                value={newExchange.api_key}
                onChange={e => setNewExchange(p => ({ ...p, api_key: e.target.value }))}
              />
            </div>
            <div>
              <Label>API Secret</Label>
              <Input
                type="password"
                value={newExchange.api_secret}
                onChange={e => setNewExchange(p => ({ ...p, api_secret: e.target.value }))}
              />
            </div>
            <div>
              <Label>Passphrase (OKX)</Label>
              <Input
                type="password"
                value={newExchange.passphrase}
                onChange={e => setNewExchange(p => ({ ...p, passphrase: e.target.value }))}
              />
            </div>
            <Button onClick={addExchange} disabled={!newExchange.api_key || !newExchange.api_secret}>
              Connect Exchange
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Risk settings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Risk Parameters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Max Order Value ($)</Label>
              <Input
                type="number"
                value={riskSettings.max_order_value_usd}
                onChange={e => setRiskSettings(p => ({ ...p, max_order_value_usd: Number(e.target.value) }))}
              />
            </div>
            <div>
              <Label>Max Daily Loss ($)</Label>
              <Input
                type="number"
                value={riskSettings.max_daily_loss_usd}
                onChange={e => setRiskSettings(p => ({ ...p, max_daily_loss_usd: Number(e.target.value) }))}
              />
            </div>
            <div>
              <Label>Max Positions</Label>
              <Input
                type="number"
                value={riskSettings.max_positions}
                onChange={e => setRiskSettings(p => ({ ...p, max_positions: Number(e.target.value) }))}
              />
            </div>
            <div className="flex items-end gap-2 pb-1">
              <Switch
                checked={riskSettings.require_confirmation}
                onCheckedChange={v => setRiskSettings(p => ({ ...p, require_confirmation: v }))}
              />
              <Label>Trade Confirmation</Label>
            </div>
          </div>
          <Button onClick={saveRiskSettings}>Save Risk Settings</Button>
        </CardContent>
      </Card>

      {/* Push settings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Push Notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            {[
              { key: 'push_morning_report', label: 'Morning Report (08:30)' },
              { key: 'push_evening_report', label: 'Evening Summary (21:00)' },
              { key: 'push_trade_alerts', label: 'Trade Alerts' },
              { key: 'push_risk_alerts', label: 'Risk Alerts' },
            ].map(({ key, label }) => (
              <div key={key} className="flex items-center justify-between">
                <Label>{label}</Label>
                <Switch
                  checked={(pushSettings as any)[key]}
                  onCheckedChange={v => setPushSettings(p => ({ ...p, [key]: v }))}
                />
              </div>
            ))}
          </div>
          <Button onClick={savePushSettings}>Save Push Settings</Button>
        </CardContent>
      </Card>
    </div>
  );
}
