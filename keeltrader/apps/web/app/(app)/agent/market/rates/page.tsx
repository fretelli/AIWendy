"use client";
import { Loader2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  agentPlatformApi,
  marketsApi,
  type RatesCatalog,
  type RatesCurve,
  type RatesSeries,
} from "@/lib/api/agent-platform";
import {
  DataLedger,
  MarketShell,
} from "../../capital/_components/market-shell";
import { NativeSeriesChart } from "../../capital/_components/native-series-chart";
export default function RatesPage() {
  const router = useRouter(),
    params = useSearchParams(),
    key = params.get("series") || "",
    field = params.get("field") || "";
  const [catalog, setCatalog] = useState<RatesCatalog | null>(null),
    [series, setSeries] = useState<RatesSeries | null>(null),
    [curve, setCurve] = useState<RatesCurve | null>(null),
    [bonds, setBonds] = useState<Array<Record<string, unknown>>>([]),
    [loading, setLoading] = useState(true);
  const select = useCallback(
    (k: string, f: string) => {
      const q = new URLSearchParams(params.toString());
      q.set("series", k);
      q.set("field", f);
      router.replace(`/agent/market/rates?${q}`);
    },
    [params, router],
  );
  useEffect(() => {
    marketsApi
      .ratesCatalog()
      .then((v) => {
        setCatalog(v);
        const c =
          v.items.find((i) => i.key === key && i.fields.includes(field)) ||
          v.items.find((i) => i.available && i.fields.length);
        if (c && (!key || !field))
          select(
            c.key,
            c.key === "repo" && c.fields.includes("weight")
              ? "weight"
              : c.fields[0],
          );
      })
      .catch((e) =>
        toast.error(e instanceof Error ? e.message : "利率目录加载失败"),
      )
      .finally(() => setLoading(false));
  }, [field, key, select]);
  useEffect(() => {
    if (!key || !field) return;
    let active = true;
    const ck = ["shibor", "us_nominal", "us_real"].includes(key)
      ? key
      : "china_cash_treasury";
    Promise.all([
      marketsApi.ratesSeries(
        key,
        field,
        key === "repo" ? { maturity: "DR007" } : {},
      ),
      marketsApi.ratesCurve(ck),
      marketsApi.convertibles(),
    ])
      .then(([s, c, b]) => {
        if (active) {
          setSeries(s);
          setCurve(c);
          setBonds(b.items);
        }
      })
      .catch((e) =>
        toast.error(e instanceof Error ? e.message : "利率债券工作区加载失败"),
      );
    return () => {
      active = false;
    };
  }, [field, key]);
  const selected = catalog?.items.find((i) => i.key === key),
    dates = useMemo(
      () => series?.rows.map((r) => String(r.period)) || [],
      [series],
    ),
    values = useMemo(
      () =>
        series?.rows.map((r) =>
          typeof r.value === "number" ? r.value : null,
        ) || [],
      [series],
    );
  const bring = async () => {
    if (!series) return;
    const s = await agentPlatformApi.createContextSnapshot({
      resource_type: "rates",
      resource_id: key,
      field,
      visible_start: series.start,
      visible_end: series.end,
      source: series.source,
      methodology:
        "完整源数据历史；中国现券国债收益率曲线未接入时明确不可用，不以期货价格替代。",
    });
    router.push(`/agent?context_snapshot=${s.id}`);
  };
  return (
    <MarketShell
      title="利率与债券"
      subtitle="资金利率、海外曲线、国债期货与可转债源数据"
      onResearch={series ? () => void bring() : undefined}
      trail={{
        object: series?.label || "利率债券",
        asOf: series?.end,
        source: series?.source,
      }}
    >
      {loading ? (
        <Loading />
      ) : (
        <PanelGroup
          direction="horizontal"
          autoSaveId="rates-market-workspace"
          className="min-h-[calc(100dvh-13rem)] overflow-hidden rounded-xl border bg-card/70"
        >
          <Panel defaultSize={21} minSize={16} maxSize={32}>
            <aside className="h-full overflow-y-auto border-r p-2">
              <p className="px-2 py-3 text-[10px] font-semibold uppercase tracking-[.18em] text-muted-foreground">
                利率目录
              </p>
              {catalog?.items.map((i) => (
                <button
                  key={i.key}
                  disabled={!i.available}
                  onClick={() =>
                    i.fields[0] &&
                    select(
                      i.key,
                      i.key === "repo" && i.fields.includes("weight")
                        ? "weight"
                        : i.fields[0],
                    )
                  }
                  className={`mb-1 w-full rounded-lg px-3 py-2.5 text-left disabled:opacity-50 ${i.key === key ? "bg-[hsl(var(--accent)/.12)] shadow-[inset_2px_0_hsl(var(--copper))]" : "hover:bg-secondary"}`}
                >
                  <span className="block text-xs font-medium">{i.label}</span>
                  <span className="text-[9px] text-muted-foreground">
                    {i.available
                      ? `${i.start} — ${i.end} · ${i.points}`
                      : i.unavailable_reason || "不可用"}
                  </span>
                </button>
              ))}
            </aside>
          </Panel>
          <Handle />
          <Panel minSize={42}>
            <main className="h-full space-y-4 overflow-y-auto p-4">
              {series && (
                <>
                  <DataLedger
                    source={series.source}
                    start={series.start}
                    end={series.end}
                    points={series.points}
                    scope="全部原始历史；无降采样、无百分位"
                  />
                  <select
                    value={field}
                    onChange={(e) => select(key, e.target.value)}
                    className="h-9 rounded-md border bg-background px-3 text-xs"
                  >
                    {selected?.fields.map((i) => <option key={i}>{i}</option>)}
                  </select>
                  <NativeSeriesChart
                    key={`${key}-${field}`}
                    dates={dates}
                    series={[
                      {
                        key: field,
                        label: field,
                        color: "hsl(var(--accent))",
                        values,
                      },
                    ]}
                  />
                </>
              )}
              <section>
                <h2 className="font-display text-lg font-semibold">曲线截面</h2>
                {curve?.available ? (
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    {curve.points.map((p) => (
                      <div
                        key={p.tenor}
                        className="rounded-lg border bg-background/60 p-3"
                      >
                        <p className="text-[10px] text-muted-foreground">
                          {p.tenor}
                        </p>
                        <p className="font-data text-sm">{p.value}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-3 rounded-lg border border-dashed p-4 text-xs text-muted-foreground">
                    {curve?.unavailable_reason || "该序列没有曲线截面。"}
                  </p>
                )}
              </section>
            </main>
          </Panel>
          <Handle />
          <Panel defaultSize={27} minSize={20} maxSize={38}>
            <aside className="h-full overflow-y-auto border-l p-4">
              <h2 className="font-display text-lg font-semibold">
                债券与来源账本
              </h2>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                国债期货对应可交割券篮子，不代表单一现券收益率。可转债保留源端转股价值与溢价率。
              </p>
              <div className="mt-4 space-y-2">
                {bonds.slice(0, 30).map((r, n) => (
                  <div
                    key={String(r.ts_code || n)}
                    className="rounded-lg border bg-background/60 p-2 text-[9px]"
                  >
                    <p className="font-data">
                      {String(r.ts_code || "—")} ·{" "}
                      {String(r.bond_short_name || "—")}
                    </p>
                    <p className="mt-1 text-muted-foreground">
                      {String(r.trade_date || "—")} · 收盘{" "}
                      {String(r.close ?? "—")} · 转股溢价{" "}
                      {String(r.cb_over_rate ?? "—")}
                    </p>
                  </div>
                ))}
              </div>
            </aside>
          </Panel>
        </PanelGroup>
      )}
    </MarketShell>
  );
}
const Handle = () => (
  <PanelResizeHandle className="w-1 bg-border/60 hover:bg-[hsl(var(--copper)/.6)]" />
);
const Loading = () => (
  <div className="grid h-80 place-items-center">
    <Loader2 className="h-7 w-7 animate-spin" />
  </div>
);
