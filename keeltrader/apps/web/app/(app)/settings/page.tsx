'use client';

import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/api/client';
import { logClientError } from '@/lib/client-log';

interface Exchange {
  id: string;
  exchange: string;
  trading_mode: string;
  is_testnet: boolean;
  last_sync: string | null;
}

interface RiskSettings {
  max_order_value_usd: number;
  max_daily_loss_usd: number;
  max_positions: number;
  require_confirmation: boolean;
}

interface PushSettings {
  push_morning_report: boolean;
  push_evening_report: boolean;
  push_trade_alerts: boolean;
  push_risk_alerts: boolean;
}

interface ResearchCloudConnection {
  status: string;
  connected: boolean;
  key_prefix?: string | null;
  plan_code?: string | null;
  user_code?: string | null;
  verification_uri?: string | null;
  device_expires_at?: string | null;
  last_error?: string | null;
  cloud_auto_context?: boolean;
}

interface NewExchangeForm {
  exchange: string;
  api_key: string;
  api_secret: string;
  passphrase: string;
  trading_mode: string;
}

const DEFAULT_RISK_SETTINGS: RiskSettings = {
  max_order_value_usd: 5000,
  max_daily_loss_usd: 500,
  max_positions: 5,
  require_confirmation: true,
};

const DEFAULT_PUSH_SETTINGS: PushSettings = {
  push_morning_report: true,
  push_evening_report: true,
  push_trade_alerts: true,
  push_risk_alerts: true,
};

const DEFAULT_NEW_EXCHANGE: NewExchangeForm = {
  exchange: 'okx',
  api_key: '',
  api_secret: '',
  passphrase: '',
  trading_mode: 'swap',
};

const PUSH_SETTING_ITEMS: Array<{ key: keyof PushSettings; label: string }> = [
  { key: 'push_morning_report', label: 'Morning Report (09:00)' },
  { key: 'push_evening_report', label: 'Evening Summary (21:00)' },
  { key: 'push_trade_alerts', label: 'Trade Alerts' },
  { key: 'push_risk_alerts', label: 'Risk Alerts' },
];

export default function SettingsPage() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [riskSettings, setRiskSettings] = useState<RiskSettings>(DEFAULT_RISK_SETTINGS);
  const [pushSettings, setPushSettings] = useState<PushSettings>(DEFAULT_PUSH_SETTINGS);
  const [researchCloud, setResearchCloud] = useState<ResearchCloudConnection>({
    status: 'disconnected',
    connected: false,
  });
  const [researchCloudAvailable, setResearchCloudAvailable] = useState(true);

  // New exchange form
  const [newExchange, setNewExchange] = useState<NewExchangeForm>(DEFAULT_NEW_EXCHANGE);

  const fetchData = useCallback(async () => {
    try {
      const [exResp, riskResp, pushResp] = await Promise.all([
        apiFetch('/settings/exchanges'),
        apiFetch('/settings/risk'),
        apiFetch('/settings/push'),
      ]);

      if (exResp.ok) {
        const data = await exResp.json();
        setExchanges(data.exchanges || []);
      }
      if (riskResp.ok) setRiskSettings(await riskResp.json());
      if (pushResp.ok) setPushSettings(await pushResp.json());
    } catch (e) {
      logClientError('settings.load', e);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void fetchData();
    });
  }, [fetchData]);

  const loadResearchCloud = useCallback(async (poll = false) => {
    try {
      const path = poll ? '/research-cloud/connection/status' : '/research-cloud/connection';
      const response = await apiFetch(path);
      if (response.status === 503) {
        setResearchCloudAvailable(false);
        return;
      }
      if (response.ok) {
        setResearchCloudAvailable(true);
        setResearchCloud(await response.json());
      }
    } catch (error) {
      logClientError('settings.research-cloud.load', error);
    }
  }, []);

  useEffect(() => {
    void loadResearchCloud();
  }, [loadResearchCloud]);

  useEffect(() => {
    if (researchCloud.status !== 'pending') return;
    const timer = window.setInterval(() => void loadResearchCloud(true), 5000);
    return () => window.clearInterval(timer);
  }, [loadResearchCloud, researchCloud.status]);

  const addExchange = async () => {
    try {
      const resp = await apiFetch('/settings/exchanges', {
        method: 'POST',
        body: newExchange,
      });
      const data = await resp.json();
      if (resp.ok) {
        toast.success(data.message || 'Connected successfully');
        setNewExchange(DEFAULT_NEW_EXCHANGE);
        fetchData();
      } else {
        toast.error(data.detail || 'Connection failed');
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Connection failed');
    }
  };

  const removeExchange = async (id: string) => {
    const resp = await apiFetch(`/settings/exchanges/${id}`, {
      method: 'DELETE',
    });
    if (resp.ok) {
      toast.success('Disconnected');
      fetchData();
    }
  };

  const saveRiskSettings = async () => {
    const resp = await apiFetch('/settings/risk', {
      method: 'PUT',
      body: riskSettings,
    });
    if (resp.ok) toast.success('Risk settings saved');
  };

  const savePushSettings = async () => {
    const resp = await apiFetch('/settings/push', {
      method: 'PUT',
      body: pushSettings,
    });
    if (resp.ok) toast.success('Push settings saved');
  };

  const connectResearchCloud = async () => {
    const response = await apiFetch('/research-cloud/connection/start', { method: 'POST' });
    if (!response.ok) {
      toast.error(response.status === 503 ? 'Research Cloud is disabled by the administrator' : 'Unable to start authorization');
      return;
    }
    setResearchCloud(await response.json());
    toast.success('Authorization code created');
  };

  const disconnectResearchCloud = async () => {
    const response = await apiFetch('/research-cloud/connection', { method: 'DELETE' });
    if (response.ok) {
      setResearchCloud(await response.json());
      toast.success('Research Cloud disconnected');
    }
  };

  const setResearchCloudAutoContext = async (enabled: boolean) => {
    const response = await apiFetch('/research-cloud/connection/preferences', {
      method: 'PUT',
      body: { cloud_auto_context: enabled },
    });
    if (response.ok) setResearchCloud(await response.json());
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 p-4 md:p-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Research Cloud</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {!researchCloudAvailable ? (
            <p className="text-sm text-muted-foreground">
              Disabled for this deployment. KeelTrader will keep all research activity local.
            </p>
          ) : researchCloud.connected ? (
            <>
              <div className="flex items-center gap-2">
                <Badge>Connected</Badge>
                <span className="text-sm text-muted-foreground">
                  {researchCloud.plan_code || 'Research plan'} · {researchCloud.key_prefix || 'secured key'}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                Only search terms, company filters and report IDs are sent. Local documents, positions,
                trades and decision journals stay on this server.
              </p>
              <div className="flex items-center justify-between rounded border p-3">
                <div>
                  <Label>Use cloud summaries in AgentOS</Label>
                  <p className="text-xs text-muted-foreground">Off by default; enable only if automatic cloud queries are acceptable.</p>
                </div>
                <Switch
                  checked={Boolean(researchCloud.cloud_auto_context)}
                  onCheckedChange={setResearchCloudAutoContext}
                />
              </div>
              <Button variant="outline" onClick={disconnectResearchCloud}>Disconnect</Button>
            </>
          ) : researchCloud.status === 'pending' ? (
            <>
              <p className="text-sm">Open Research and approve this device code:</p>
              <div className="font-mono text-2xl tracking-widest">{researchCloud.user_code}</div>
              {researchCloud.verification_uri && (
                <a className="text-sm text-primary underline" href={researchCloud.verification_uri} target="_blank" rel="noreferrer">
                  Open authorization page
                </a>
              )}
              <p className="text-xs text-muted-foreground">Waiting for approval; this page checks every 5 seconds.</p>
            </>
          ) : (
            <>
              {researchCloud.last_error && <p className="text-sm text-destructive">{researchCloud.last_error}</p>}
              <p className="text-sm text-muted-foreground">
                Optional. Connecting does not share your local knowledge base or model API keys.
              </p>
              <Button onClick={connectResearchCloud}>Connect Research Cloud</Button>
            </>
          )}
        </CardContent>
      </Card>

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
            {PUSH_SETTING_ITEMS.map(({ key, label }) => (
              <div key={key} className="flex items-center justify-between">
                <Label>{label}</Label>
                <Switch
                  checked={pushSettings[key]}
                  onCheckedChange={v => setPushSettings(p => ({ ...p, [key]: v }))}
                />
              </div>
            ))}
          </div>
          <Button onClick={savePushSettings}>Save Push Settings</Button>
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
