"use client";

import { Loader2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  agentPlatformApi,
  marketsApi,
  type MarketUnderlying,
  type OptionExposures,
  type OptionSeries,
  type OptionSurface,
  type OptionsChain,
  type OptionsHistory,
  type OptionsSeriesResponse,
  type UnderlyingSeries,
} from "@/lib/api/agent-platform";
import { DataLedger, MarketShell } from "../_components/market-shell";
import { NativeSeriesChart } from "../_components/native-series-chart";

type Field = "volume" | "amount" | "oi" | "contracts";
type ResourceKey =
  | "history"
  | "chain"
  | "underlying"
  | "underlyingSeries"
  | "surface"
  | "exposures";
const fieldNames: Record<Field, string> = {
  volume: "成交量",
  amount: "成交额",
  oi: "持仓量",
  contracts: "合约数",
};
export default function OptionsMarketPage() {
  const router = useRouter(),
    params = useSearchParams(),
    code = params.get("code") || "",
    field = (params.get("field") as Field) || "volume",
    maturity = params.get("maturity") || "";
  const [catalog, setCatalog] = useState<OptionsSeriesResponse | null>(null),
    [history, setHistory] = useState<OptionsHistory | null>(null),
    [chain, setChain] = useState<OptionsChain | null>(null),
    [surface, setSurface] = useState<OptionSurface | null>(null),
    [exposures, setExposures] = useState<OptionExposures | null>(null),
    [underlying, setUnderlying] = useState<MarketUnderlying | null>(null),
    [underlyingSeries, setUnderlyingSeries] = useState<UnderlyingSeries | null>(
      null,
    ),
    [loading, setLoading] = useState(true),
    [refreshing, setRefreshing] = useState(false),
    [query, setQuery] = useState(""),
    [resourceErrors, setResourceErrors] = useState<
      Partial<Record<ResourceKey, string>>
    >({}),
    [reloadToken, setReloadToken] = useState(0);
  const select = useCallback(
    (nextCode: string, nextField: Field = field, nextMaturity = "") => {
      const q = new URLSearchParams(params.toString());
      q.set("code", nextCode);
      q.set("field", nextField);
      nextMaturity ? q.set("maturity", nextMaturity) : q.delete("maturity");
      router.replace(`/agent/market/options?${q}`);
    },
    [field, params, router],
  );
  const loadCatalog = useCallback(
    async (refresh = false) => {
      refresh ? setRefreshing(true) : setLoading(true);
      try {
        const result = await marketsApi.optionsCatalog();
        setCatalog(result);
        if (!code && result.items[0]) select(result.items[0].opt_code);
      } catch (error) {
        toast.error(
          error instanceof Error ? error.message : "期权目录加载失败",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [code, select],
  );
  useEffect(() => {
    queueMicrotask(() => void loadCatalog());
  }, [loadCatalog]);
  useEffect(() => {
    if (!code) return;
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setHistory(null);
      setChain(null);
      setSurface(null);
      setExposures(null);
      setUnderlying(null);
      setUnderlyingSeries(null);
      setResourceErrors({});
    });
    Promise.allSettled([
      marketsApi.optionsHistory(code),
      marketsApi.optionsChain(code, {
        maturity: maturity || undefined,
        limit: 500,
      }),
      marketsApi.optionUnderlying(code),
      marketsApi.optionSurface(code),
      marketsApi.optionExposures(code),
    ])
      .then(async ([h, c, u, s, e]) => {
        if (!active) return;
        const nextErrors: Partial<Record<ResourceKey, string>> = {};
        if (h.status === "fulfilled") setHistory(h.value);
        else nextErrors.history = errorText(h.reason, "期权历史加载失败");
        if (c.status === "fulfilled") setChain(c.value);
        else nextErrors.chain = errorText(c.reason, "期权链加载失败");
        if (s.status === "fulfilled") setSurface(s.value);
        else nextErrors.surface = errorText(s.reason, "IV 与 Greeks 加载失败");
        if (e.status === "fulfilled") setExposures(e.value);
        else nextErrors.exposures = errorText(e.reason, "敏感度敞口加载失败");
        if (u.status === "fulfilled") {
          setUnderlying(u.value);
          if (
            u.value.series_available &&
            u.value.code &&
            ["index", "etf", "futures_contract"].includes(u.value.relationship)
          ) {
            try {
              setUnderlyingSeries(
                await marketsApi.underlyingSeries(
                  u.value.relationship,
                  u.value.code,
                ),
              );
            } catch (error) {
              nextErrors.underlyingSeries = errorText(
                error,
                "底层标的历史加载失败",
              );
            }
          }
        } else {
          nextErrors.underlying = errorText(u.reason, "底层关系加载失败");
        }
        if (active) setResourceErrors(nextErrors);
      });
    return () => {
      active = false;
    };
  }, [code, maturity, reloadToken]);
  const rows = history?.history || [],
    selected = catalog?.items.find((item) => item.opt_code === code),
    visible = useMemo(() => {
      const needle = query.trim().toLowerCase();
      return (catalog?.items || []).filter(
        (item) =>
          !needle ||
          `${item.opt_code}${item.exchange}${item.underlying_code || ""}`
            .toLowerCase()
            .includes(needle),
      );
    }, [catalog, query]),
    maturities = useMemo(
      () =>
        Array.from(
          new Set(
            (chain?.items || [])
              .map((item) => item.maturity_date)
              .filter(Boolean) as string[],
          ),
        ),
      [chain],
    );
  const bring = async () => {
    if (!history) return;
    const snapshot = await agentPlatformApi.createContextSnapshot({
      resource_type: "options",
      resource_id: code,
      field,
      visible_start: history.history_meta.start_date,
      visible_end: history.history_meta.end_date,
      selected_point: maturity ? { maturity } : undefined,
      source: history.history_meta.source,
      methodology:
        "期权历史由 opt_daily 与 opt_basic 原始行聚合，并叠加可审计 IV/Greeks；OI 敏感度为 gross OI-weighted sensitivity，不代表做市商净头寸。",
    });
    router.push(
      `/agent?context_snapshot=${snapshot.id}&context_label=${encodeURIComponent(`${code}·${field}`)}`,
    );
  };
  return (
    <MarketShell
      title="期权市场"
      subtitle="底层标的 → 到期日 → 原始期权链"
      refreshing={refreshing}
      onRefresh={() => {
        void loadCatalog(true);
        setReloadToken((value) => value + 1);
      }}
      onResearch={history ? () => void bring() : undefined}
      trail={{
        object: code || "期权序列",
        asOf: history?.history_meta.end_date,
        source: history?.history_meta.source,
      }}
    >
      {loading && !catalog ? (
        <Loading />
      ) : (
        <PanelGroup
          direction="horizontal"
          autoSaveId="options-market-workspace"
          className="min-h-[calc(100dvh-13rem)] overflow-hidden rounded-xl border bg-card/70"
        >
          <Panel defaultSize={21} minSize={16} maxSize={32}>
            <aside className="h-full overflow-y-auto border-r p-2">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索序列或交易所"
                className="mb-2 h-9 w-full rounded-md border bg-background px-3 text-xs"
              />
              {visible.map((item) => (
                <SeriesButton
                  key={item.opt_code}
                  item={item}
                  active={item.opt_code === code}
                  onClick={() => select(item.opt_code)}
                />
              ))}
            </aside>
          </Panel>
          <Handle />
          <Panel minSize={42}>
            <main className="h-full space-y-4 overflow-y-auto p-4">
              <div className="flex flex-wrap gap-2">
                {(Object.keys(fieldNames) as Field[]).map((key) => (
                  <Button
                    key={key}
                    size="sm"
                    variant={field === key ? "default" : "outline"}
                    onClick={() => select(code, key, maturity)}
                  >
                    {fieldNames[key]}
                  </Button>
                ))}
              </div>
              <DataLedger
                source={
                  history?.history_meta.source || "tushare.opt_series_daily"
                }
                start={history?.history_meta.start_date}
                end={history?.history_meta.end_date}
                points={history?.history_meta.points}
                scope="当前已同步的全部原始历史"
              />
              {resourceErrors.history ? (
                <ResourceError
                  message={resourceErrors.history}
                  onRetry={() => setReloadToken((value) => value + 1)}
                />
              ) : (
                <NativeSeriesChart
                  key={`${code}-${field}`}
                  dates={rows.map((row) => row.trade_date)}
                  series={[
                    {
                      key: `call_${field}`,
                      label: "看涨",
                      color: "#d95d6f",
                      values: rows.map((row) =>
                        numberOrNull(row[`call_${field}` as keyof typeof row]),
                      ),
                    },
                    {
                      key: `put_${field}`,
                      label: "看跌",
                      color: "#238d72",
                      values: rows.map((row) =>
                        numberOrNull(row[`put_${field}` as keyof typeof row]),
                      ),
                    },
                  ]}
                />
              )}
              {underlyingSeries && (
                <section>
                  <h2 className="mb-2 font-display text-lg font-semibold">
                    底层标的原始历史 · {underlying?.name}
                  </h2>
                  <NativeSeriesChart
                    key={underlyingSeries.code}
                    dates={underlyingSeries.rows.map((row) => row.trade_date)}
                    series={[
                      {
                        key: "close",
                        label: "底层收盘",
                        color: "hsl(var(--copper-foreground))",
                        values: underlyingSeries.rows.map((row) =>
                          numberOrNull(row.close),
                        ),
                      },
                    ]}
                  />
                </section>
              )}
              {resourceErrors.underlyingSeries && (
                <ResourceError
                  message={resourceErrors.underlyingSeries}
                  onRetry={() => setReloadToken((value) => value + 1)}
                />
              )}
              <section>
                <h2 className="mb-2 font-display text-lg font-semibold">
                  IV 与 Greeks · {surface?.trade_date || "不可用"}
                </h2>
                <p className="mb-3 text-[10px] text-muted-foreground">
                  逐合约源点，不做曲面插值。欧式现货 BSM、欧式期货 Black–76、美式期货 CRR；结算价优先，收盘价仅作标记回退。
                </p>
                {resourceErrors.surface ? (
                  <ResourceError
                    message={resourceErrors.surface}
                    onRetry={() => setReloadToken((value) => value + 1)}
                  />
                ) : (
                  <div className="max-h-72 overflow-auto rounded-xl border">
                    <table className="w-full text-left text-[9px]">
                      <thead className="sticky top-0 bg-card">
                        <tr>
                          <th className="p-2">合约</th>
                          <th>行权价</th>
                          <th>IV</th>
                          <th>Delta</th>
                          <th>Gamma</th>
                          <th>Vega</th>
                          <th>状态</th>
                        </tr>
                      </thead>
                      <tbody>
                        {surface?.items
                          .filter(
                            (item) =>
                              !maturity || item.maturity_date === maturity,
                          )
                          .map((item) => (
                            <tr key={item.ts_code} className="border-t">
                              <td className="p-2 font-data">{item.ts_code}</td>
                              <td>{fmt(item.exercise_price)}</td>
                              <td>{fmt(item.implied_volatility)}</td>
                              <td>{fmt(item.delta)}</td>
                              <td>{fmt(item.gamma)}</td>
                              <td>{fmt(item.vega)}</td>
                              <td title={item.unavailable_reason}>
                                {item.convergence_status}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <h3 className="mt-4 text-xs font-semibold">
                  Gross OI-weighted sensitivity
                </h3>
                {resourceErrors.exposures ? (
                  <ResourceError
                    message={resourceErrors.exposures}
                    onRetry={() => setReloadToken((value) => value + 1)}
                  />
                ) : (
                  <p className="mt-1 text-[9px] text-muted-foreground">
                    {exposures?.methodology}
                  </p>
                )}
              </section>
            </main>
          </Panel>
          <Handle />
          <Panel defaultSize={27} minSize={20} maxSize={38}>
            <aside className="h-full overflow-y-auto border-l p-4">
              <h2 className="font-display text-lg font-semibold">底层关系与模型</h2>
              {resourceErrors.underlying && (
                <ResourceError
                  message={resourceErrors.underlying}
                  onRetry={() => setReloadToken((value) => value + 1)}
                />
              )}
              <div className="mt-3 rounded-xl border bg-background/60 p-3 text-xs">
                <p className="font-medium">{underlying?.name || "未解析"}</p>
                <p className="mt-1 font-data text-[9px] text-muted-foreground">
                  {underlying?.relationship} · {underlying?.code || "—"}
                </p>
                <p className="mt-3 leading-5 text-muted-foreground">
                  {underlying?.methodology}
                </p>
              </div>
              <div className="mt-4">
                <label className="text-[10px] text-muted-foreground">
                  到期日
                </label>
                <select
                  value={maturity}
                  onChange={(event) => select(code, field, event.target.value)}
                  className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-xs"
                >
                  <option value="">全部可用到期日</option>
                  {maturities.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </div>
              <h3 className="mt-5 text-xs font-semibold">
                原始期权链 · {chain?.trade_date} · {chain?.total || 0}条
              </h3>
              {resourceErrors.chain && (
                <ResourceError
                  message={resourceErrors.chain}
                  onRetry={() => setReloadToken((value) => value + 1)}
                />
              )}
              <div className="mt-2 max-h-[48vh] overflow-auto">
                <table className="w-full text-left text-[9px]">
                  <thead className="sticky top-0 bg-card">
                    <tr>
                      <th className="py-2">合约</th>
                      <th>方向</th>
                      <th>行权价</th>
                      <th>收盘</th>
                      <th>OI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {chain?.items.map((item) => (
                      <tr key={item.ts_code} className="border-t">
                        <td className="py-2 font-data">{item.ts_code}</td>
                        <td>{item.call_put === "C" ? "涨" : "跌"}</td>
                        <td>{fmt(item.exercise_price)}</td>
                        <td>{fmt(item.close)}</td>
                        <td>{fmt(item.oi)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </aside>
          </Panel>
        </PanelGroup>
      )}
    </MarketShell>
  );
}
function ResourceError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="my-3 rounded-xl border border-amber-500/40 bg-amber-500/[.06] p-3 text-[10px]">
      <p className="leading-5 text-amber-800 dark:text-amber-200">{message}</p>
      <Button className="mt-2" size="sm" variant="outline" onClick={onRetry}>
        重新读取
      </Button>
    </div>
  );
}
function errorText(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? `${fallback}：${error.message}` : fallback;
}
function SeriesButton({
  item,
  active,
  onClick,
}: {
  item: OptionSeries;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`mb-1 w-full rounded-lg px-3 py-2.5 text-left ${active ? "bg-[hsl(var(--accent)/.12)] shadow-[inset_2px_0_hsl(var(--copper))]" : "hover:bg-secondary"}`}
    >
      <span className="block font-data text-xs font-medium">
        {item.underlying_code || "未解析"} → {item.opt_code}
      </span>
      <span className="text-[9px] text-muted-foreground">
        {item.underlying_type} · {item.latest_maturity || "—"} ·{" "}
        {item.active_contracts}活跃
      </span>
    </button>
  );
}
const Handle = () => (
  <PanelResizeHandle className="w-1 bg-border/60 hover:bg-[hsl(var(--copper)/.6)]" />
);
const numberOrNull = (value: unknown) =>
  typeof value === "number" && Number.isFinite(value) ? value : null;
const fmt = (value?: number) =>
  value == null
    ? "—"
    : value.toLocaleString("zh-CN", { maximumFractionDigits: 4 });
const Loading = () => (
  <div className="grid h-80 place-items-center">
    <Loader2 className="h-7 w-7 animate-spin" />
  </div>
);
