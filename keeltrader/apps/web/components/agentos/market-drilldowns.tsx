"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { EmptyPanel, Panel, SectionTitle, StatusDot } from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { marketsApi, type FuturesCurve, type FuturesHistory, type FuturesProduct, type OptionSeries, type OptionsChain, type RatesCatalog, type RatesCurve, type RatesSeries } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

const TimeSeriesChart = dynamic(() => import("@/components/agentos/market-charts").then((module) => module.TimeSeriesChart), { ssr: false });
const HISTORY_RANGES = ["1M", "3M", "1Y", "3Y", "5Y"] as const;
const RATE_HISTORY_RANGES = [...HISTORY_RANGES, "10Y", "ALL"] as const;
type HistoryRange = (typeof HISTORY_RANGES)[number];
type RateHistoryRange = (typeof RATE_HISTORY_RANGES)[number];

export function RatesDrilldown() {
  const { locale } = useI18n();
  const [catalog, setCatalog] = useState<RatesCatalog | null>(null);
  const [selected, setSelected] = useState<string>();
  const [field, setField] = useState<string>();
  const [range, setRange] = useState<RateHistoryRange>("1Y");
  const [series, setSeries] = useState<RatesSeries>();
  const [curve, setCurve] = useState<RatesCurve>();
  useEffect(() => { void marketsApi.ratesCatalog().then((data) => { const initial = data.items.find((entry) => entry.available); setCatalog(data); setSelected(initial?.key); setField(initial?.primary_field && initial.fields.includes(initial.primary_field) ? initial.primary_field : initial?.fields[0]); }).catch(() => setCatalog(null)); }, []);
  const item = catalog?.items.find((entry) => entry.key === selected);
  useEffect(() => {
    if (!item?.available || !field) return;
    void marketsApi.ratesSeries(item.key, field).then(setSeries).catch(() => setSeries(undefined));
    if (["shibor", "hibor", "libor_usd", "us_nominal", "us_real", "us_short", "us_long", "us_real_long_average"].includes(item.key)) void marketsApi.ratesCurve(item.key).then(setCurve).catch(() => setCurve(undefined));
  }, [field, item?.available, item?.key]);
  const chooseRate = (key: string) => {
    const next = catalog?.items.find((entry) => entry.key === key);
    setSelected(key); setSeries(undefined); setCurve(undefined);
    setField(next?.primary_field && next.fields.includes(next.primary_field) ? next.primary_field : next?.fields[0]);
  };
  const visible = series?.rows.slice(-periodPoints(range)) || [];
  return <div className="grid gap-3"><Panel><SectionTitle title={locale === "zh" ? "利率与收益率" : "Rates & Yields"} en="PROVIDER-NATIVE SERIES" />
    {catalog?.items.length ? <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">{catalog.items.map((entry) => <button type="button" onClick={() => chooseRate(entry.key)} key={entry.key} className={`rounded-md border bg-agent-raised p-3 text-left ${selected === entry.key ? "border-agent-mint" : "border-agent-border"}`}><div className="flex items-center gap-2"><StatusDot status={entry.available ? "complete" : "unavailable"} /><span className="text-xs text-agent-text">{entry.label}</span></div><p className="mt-3 font-data text-[9px] text-agent-dim">{entry.start || "—"} → {entry.end || "—"} · {entry.points || 0} {locale === "zh" ? "个观测值" : "points"}</p>{entry.freshness_note ? <p className="mt-2 text-[9px] leading-4 text-agent-amber">{historicalSourceNote(entry, locale)}</p> : null}{entry.unavailable_reason ? <p className="mt-2 text-[10px] leading-5 text-agent-amber">{localizeUnavailableReason(entry.unavailable_reason, locale)}</p> : null}</button>)}</div> : <EmptyPanel title={locale === "zh" ? "利率目录不可用" : "Rates catalog unavailable"} detail={locale === "zh" ? "yc_cb 等缺失来源会保持明确不可用，不使用期货或合成曲线。" : "Missing sources such as yc_cb remain explicitly unavailable without futures or synthetic substitutes."} />}
  </Panel>{item?.available ? <Panel><SectionTitle title={item.label} en="HISTORY · LATEST CURVE" /><div className="mb-3 flex flex-wrap gap-2"><ToggleGroup type="single" value={field} onValueChange={(value) => { if (value) setField(value); }} variant="outline" size="sm" aria-label={locale === "zh" ? "利率字段" : "Rate field"}>{item.fields.map((value) => <ToggleGroupItem key={value} value={value} className="font-data text-[9px]">{rateFieldLabel(value, locale)}</ToggleGroupItem>)}</ToggleGroup><ToggleGroup type="single" value={range} onValueChange={(value) => { if (value) setRange(value as RateHistoryRange); }} variant="outline" size="sm" aria-label={locale === "zh" ? "历史范围" : "History range"}>{RATE_HISTORY_RANGES.map((value) => <ToggleGroupItem key={value} value={value} className="font-data text-[9px]">{value}</ToggleGroupItem>)}</ToggleGroup></div>{visible.length ? <TimeSeriesChart dates={visible.map((row) => row.period)} series={[{ name: rateFieldLabel(field || "", locale), values: visible.map((row) => row.value) }]} locale={locale} title={`${item.label} · ${range}`} height={340} /> : <EmptyPanel title={locale === "zh" ? "该字段没有历史" : "No history for this field"} detail="" />}{curve?.points.length ? <div className="mt-4 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">{curve.points.map((point) => <div key={point.tenor} className="rounded border border-agent-border bg-agent-raised p-2"><p className="font-data text-[9px] text-agent-dim">{rateFieldLabel(point.tenor, locale)}</p><p className="mt-1 font-data text-sm text-agent-blue">{Number(point.value).toFixed(3)}%</p></div>)}</div> : null}</Panel> : null}</div>;
}

function rateFieldLabel(field: string, locale: "zh" | "en") {
  const zh: Record<string, string> = { on: "隔夜", "1w": "1周", "2w": "2周", "1m": "1月", "2m": "2月", "3m": "3月", "6m": "6月", "9m": "9月", "12m": "12月", "1y": "1年", "5y": "5年", m1: "1月", m2: "2月", m3: "3月", m6: "6月", y1: "1年", y2: "2年", y3: "3年", y5: "5年", y7: "7年", y10: "10年", y20: "20年", y30: "30年", comp_rate: "综合利率", center_rate: "民间借贷服务中心", micro_rate: "小额贷款公司", cm_rate: "民间资本管理公司", sdb_rate: "社会直接借贷", om_rate: "其他市场主体", aa_rate: "农村互助会", d10_rate: "10天", m1_rate: "1月", m3_rate: "3月", m6_rate: "6月", m12_rate: "12月", long_rate: "长期", w4_bd: "4周贴现", w4_ce: "4周票息等价", w8_bd: "8周贴现", w8_ce: "8周票息等价", w13_bd: "13周贴现", w13_ce: "13周票息等价", w17_bd: "17周贴现", w17_ce: "17周票息等价", w26_bd: "26周贴现", w26_ce: "26周票息等价", w52_bd: "52周贴现", w52_ce: "52周票息等价", ltc: "长期复合利率", cmt: "20年CMT", ltr_avg: "10年以上实际平均利率" };
  return locale === "zh" ? zh[field] || field : field.toUpperCase();
}

function historicalSourceNote(entry: RatesCatalog["items"][number], locale: "zh" | "en") {
  if (locale === "zh") return entry.freshness_note;
  if (entry.key === "wenzhou_private") return "Provider history ends on 2023-03-08; no synthetic continuation.";
  if (entry.key === "guangzhou_private") return "Provider history ends on 2019-03-04; no synthetic continuation.";
  return "Provider history ends on 2020-06-24; no synthetic continuation.";
}

export function FuturesDrilldown() {
  const { locale } = useI18n();
  const [items, setItems] = useState<FuturesProduct[]>([]);
  const [selected, setSelected] = useState<string>();
  const [range, setRange] = useState<HistoryRange>("1Y");
  const [history, setHistory] = useState<FuturesHistory>();
  const [curve, setCurve] = useState<FuturesCurve>();
  useEffect(() => { void marketsApi.futuresProducts().then((data) => { setItems(data.items); setSelected(data.items[0]?.product_code); }); }, []);
  useEffect(() => { if (!selected) return; void Promise.all([marketsApi.futuresHistory(selected), marketsApi.futuresCurve(selected)]).then(([nextHistory, nextCurve]) => { setHistory(nextHistory); setCurve(nextCurve); }); }, [selected]);
  const visibleHistory = history?.history.slice(-periodPoints(range)) || [];
  return <div className="grid gap-3 xl:grid-cols-[280px_1fr]"><Panel><SectionTitle title={locale === "zh" ? "期货品种" : "Futures Products"} en="PUBLISHED CONTRACTS" /><div className="flex max-h-[430px] flex-col gap-1 overflow-y-auto">{items.map((item) => <Button key={item.product_code} variant={selected === item.product_code ? "secondary" : "ghost"} className="justify-between" onClick={() => setSelected(item.product_code)}><span>{item.product_code}</span><span className="font-data text-[9px] text-agent-dim">{item.trade_date}</span></Button>)}</div></Panel><Panel><SectionTitle title={selected || (locale === "zh" ? "期限结构" : "Term Structure")} en="HISTORY · CURVE" /><ToggleGroup type="single" value={range} onValueChange={(value) => { if (value) setRange(value as HistoryRange); }} variant="outline" size="sm" aria-label={locale === "zh" ? "当前期货历史范围" : "Current futures history range"} className="mb-3 flex-wrap justify-start">{HISTORY_RANGES.map((value) => <ToggleGroupItem key={value} value={value} aria-label={value} className="font-data text-[10px] data-[state=on]:bg-agent-mint data-[state=on]:text-agent-canvas">{value}</ToggleGroupItem>)}</ToggleGroup>{visibleHistory.length ? <><TimeSeriesChart dates={visibleHistory.map((item) => item.trade_date)} series={[{ name: locale === "zh" ? "结算价 / 收盘价" : "Settlement / Close", values: visibleHistory.map((item) => item.settle ?? item.close ?? null) }]} locale={locale} title={`${selected || "—"} · ${range}`} height={320} /><div className="mt-4 grid gap-2 md:grid-cols-3">{curve?.items.slice(0, 12).map((item) => <div key={item.contract_code} className="rounded border border-agent-border bg-agent-raised p-3"><p className="text-xs text-agent-text">{item.contract_code}</p><p className="mt-2 font-data text-sm text-agent-blue">{item.settle ?? item.close ?? "—"}</p><p className="mt-1 text-[9px] text-agent-dim">{locale === "zh" ? "持仓量" : "Open interest"} {item.oi ?? "—"}</p></div>)}</div></> : <EmptyPanel title={locale === "zh" ? "选择有历史的品种" : "Select a product with history"} detail={locale === "zh" ? "只展示原始期货行情与可审计合约映射。" : "Only raw futures data and audited contract mappings are shown."} />}</Panel></div>;
}

export function OptionsDrilldown() {
  const { locale } = useI18n();
  const [items, setItems] = useState<OptionSeries[]>([]);
  const [selected, setSelected] = useState<string>();
  const [chain, setChain] = useState<OptionsChain>();
  useEffect(() => { void marketsApi.optionsCatalog().then((data) => { setItems(data.items); setSelected(data.items[0]?.opt_code); }); }, []);
  useEffect(() => { if (!selected) return; void marketsApi.optionsChain(selected, { limit: 120 }).then(setChain); }, [selected]);
  return <div className="grid gap-3 xl:grid-cols-[280px_1fr]"><Panel><SectionTitle title={locale === "zh" ? "期权底层" : "Option Underlyings"} en="AUDITED MAPPING" /><div className="flex max-h-[430px] flex-col gap-1 overflow-y-auto">{items.map((item) => <Button key={item.opt_code} variant={selected === item.opt_code ? "secondary" : "ghost"} className="justify-between" onClick={() => setSelected(item.opt_code)}><span>{item.opt_code}</span><span className="font-data text-[9px] text-agent-dim">{item.active_contracts}</span></Button>)}</div></Panel><Panel><SectionTitle title={selected || (locale === "zh" ? "期权链" : "Option Chain")} en="IV · GREEKS · RAW QUOTES" />{chain?.items.length ? <div className="overflow-x-auto"><table className="w-full text-left text-[10px]"><thead className="font-data text-agent-dim"><tr><th className="p-2">{locale === "zh" ? "合约" : "Contract"}</th><th className="p-2">{locale === "zh" ? "认购/认沽" : "Call/Put"}</th><th className="p-2">{locale === "zh" ? "行权价" : "Strike"}</th><th className="p-2">{locale === "zh" ? "到期日" : "Maturity"}</th><th className="p-2 text-right">{locale === "zh" ? "结算价" : "Settlement"}</th><th className="p-2 text-right">{locale === "zh" ? "持仓量" : "Open interest"}</th></tr></thead><tbody>{chain.items.map((item) => <tr key={item.ts_code} className="border-t border-agent-border"><td className="p-2 text-agent-text">{item.ts_code}</td><td className="p-2 text-agent-muted">{item.call_put}</td><td className="p-2 font-data">{item.exercise_price ?? "—"}</td><td className="p-2 font-data text-agent-dim">{item.maturity_date}</td><td className="p-2 text-right font-data">{item.settle ?? item.close ?? "—"}</td><td className="p-2 text-right font-data">{item.oi ?? "—"}</td></tr>)}</tbody></table></div> : <EmptyPanel title={locale === "zh" ? "期权链不可用" : "Option chain unavailable"} detail={locale === "zh" ? "不会使用演示波动率曲面或 Greeks。" : "No demo volatility surface or Greeks are substituted."} />}</Panel></div>;
}

function localizeUnavailableReason(reason: string, locale: "zh" | "en") {
  if (locale === "en") return reason;
  const known: Record<string, string> = {
    permission_denied: "上游权限不足。",
    provider_permission_denied: "上游权限不足。",
    not_ingested: "尚未接入正式数据。",
    publication_pending: "等待正式数据发布。",
  };
  return known[reason] || "该正式数据源当前不可用。";
}

function periodPoints(period: HistoryRange | RateHistoryRange) {
  return ({ "1M": 22, "3M": 66, "1Y": 252, "3Y": 756, "5Y": 1260, "10Y": 2520, ALL: Number.MAX_SAFE_INTEGER } as const)[period];
}
