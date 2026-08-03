"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { EmptyPanel, Panel, SectionTitle, StatusDot } from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { marketsApi, type FuturesCurve, type FuturesHistory, type FuturesProduct, type OptionSeries, type OptionsChain, type RatesCatalog } from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

const TimeSeriesChart = dynamic(() => import("@/components/agentos/market-charts").then((module) => module.TimeSeriesChart), { ssr: false });
type Period = "1M" | "3M" | "1Y" | "3Y";

export function RatesDrilldown() {
  const { locale } = useI18n();
  const [catalog, setCatalog] = useState<RatesCatalog | null>(null);
  useEffect(() => { void marketsApi.ratesCatalog().then(setCatalog).catch(() => setCatalog(null)); }, []);
  return <Panel><SectionTitle title={locale === "zh" ? "利率与债券" : "Rates & Bonds"} en="PROVIDER-NATIVE SERIES" />
    {catalog?.items.length ? <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">{catalog.items.map((item) => <div key={item.key} className="rounded-md border border-agent-border bg-agent-raised p-3"><div className="flex items-center gap-2"><StatusDot status={item.available ? "complete" : "unavailable"} /><span className="text-xs text-agent-text">{item.label}</span></div><p className="mt-3 font-data text-[9px] text-agent-dim">{item.start || "—"} → {item.end || "—"} · {item.points || 0} {locale === "zh" ? "个观测值" : "points"}</p>{item.unavailable_reason ? <p className="mt-2 text-[10px] leading-5 text-agent-amber">{localizeUnavailableReason(item.unavailable_reason, locale)}</p> : null}</div>)}</div> : <EmptyPanel title={locale === "zh" ? "利率目录不可用" : "Rates catalog unavailable"} detail={locale === "zh" ? "yc_cb 等缺失来源会保持明确不可用，不使用期货或合成曲线。" : "Missing sources such as yc_cb remain explicitly unavailable without futures or synthetic substitutes."} />}
  </Panel>;
}

export function FuturesDrilldown({ period = "1Y" }: { period?: Period }) {
  const { locale } = useI18n();
  const [items, setItems] = useState<FuturesProduct[]>([]);
  const [selected, setSelected] = useState<string>();
  const [history, setHistory] = useState<FuturesHistory>();
  const [curve, setCurve] = useState<FuturesCurve>();
  useEffect(() => { void marketsApi.futuresProducts().then((data) => { setItems(data.items); setSelected(data.items[0]?.product_code); }); }, []);
  useEffect(() => { if (!selected) return; void Promise.all([marketsApi.futuresHistory(selected), marketsApi.futuresCurve(selected)]).then(([nextHistory, nextCurve]) => { setHistory(nextHistory); setCurve(nextCurve); }); }, [selected]);
  const visibleHistory = history?.history.slice(-periodPoints(period)) || [];
  return <div className="grid gap-3 xl:grid-cols-[280px_1fr]"><Panel><SectionTitle title={locale === "zh" ? "期货品种" : "Futures Products"} en="PUBLISHED CONTRACTS" /><div className="flex max-h-[430px] flex-col gap-1 overflow-y-auto">{items.map((item) => <Button key={item.product_code} variant={selected === item.product_code ? "secondary" : "ghost"} className="justify-between" onClick={() => setSelected(item.product_code)}><span>{item.product_code}</span><span className="font-data text-[9px] text-agent-dim">{item.trade_date}</span></Button>)}</div></Panel><Panel><SectionTitle title={selected || (locale === "zh" ? "期限结构" : "Term Structure")} en="HISTORY · CURVE" />{visibleHistory.length ? <><TimeSeriesChart dates={visibleHistory.map((item) => item.trade_date)} series={[{ name: locale === "zh" ? "结算价 / 收盘价" : "Settlement / Close", values: visibleHistory.map((item) => item.settle ?? item.close ?? null) }]} locale={locale} title={`${selected || "—"} · ${period}`} height={320} /><div className="mt-4 grid gap-2 md:grid-cols-3">{curve?.items.slice(0, 12).map((item) => <div key={item.contract_code} className="rounded border border-agent-border bg-agent-raised p-3"><p className="text-xs text-agent-text">{item.contract_code}</p><p className="mt-2 font-data text-sm text-agent-blue">{item.settle ?? item.close ?? "—"}</p><p className="mt-1 text-[9px] text-agent-dim">{locale === "zh" ? "持仓量" : "Open interest"} {item.oi ?? "—"}</p></div>)}</div></> : <EmptyPanel title={locale === "zh" ? "选择有历史的品种" : "Select a product with history"} detail={locale === "zh" ? "只展示原始期货行情与可审计合约映射。" : "Only raw futures data and audited contract mappings are shown."} />}</Panel></div>;
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

function periodPoints(period: Period) {
  return ({ "1M": 22, "3M": 66, "1Y": 252, "3Y": 756 } as const)[period];
}
