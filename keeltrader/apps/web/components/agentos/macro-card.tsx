"use client";

import { MiniLine } from "@/components/agentos/dashboard-ui";
import type { MacroCatalog, MacroMetricSummary } from "@/lib/api/agent-platform";
import { cn } from "@/lib/utils";

export function MacroCard({ row, locale, onOpenAnalysis, onOpenField, onOpenAll }: { row: MacroCatalog["items"][number]; locale: "zh" | "en"; onOpenAnalysis: () => void; onOpenField: (field: string) => void; onOpenAll: () => void }) {
  const summary = row.summary;
  const sparkline = (row.sparkline?.values || []).filter((value): value is number => typeof value === "number");
  const featured = row.featured_fields || [];
  return <article className={cn("min-h-[154px] rounded-sm border border-agent-border bg-agent-surface p-3 transition-colors", row.available ? "hover:border-agent-blue/40" : "opacity-75")}>
    {row.available ? <button type="button" onClick={onOpenAnalysis} className="block w-full rounded-sm text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-agent-mint"><div className="flex items-start justify-between gap-2"><div><p className="text-[11px] text-agent-text">{macroLabel(row.key, locale)}</p><p className="mt-1 font-data text-[8px] text-agent-dim">{macroSourceNote(row, locale)}</p>{row.next_release ? <p className="mt-1 font-data text-[8px] text-agent-amber">{locale === "zh" ? "下次发布" : "Next release"} {row.next_release.release_date} {row.next_release.release_time || ""}{row.next_release.status === "awaiting_source_value" ? (locale === "zh" ? " · 等待源端实际值" : " · awaiting source value") : ""}</p> : null}</div><MacroMetricCell metric={summary?.primary} locale={locale} emphasis /></div><div className="mt-3 grid grid-cols-3 gap-2 border-t border-agent-border pt-2"><div><p className="font-data text-[7px] text-agent-dim">{macroSequentialLabel(row.key, locale)}</p><MacroMetricCell metric={summary?.mom} locale={locale} signed /></div><div><p className="font-data text-[7px] text-agent-dim">{locale === "zh" ? "同比比较" : "YoY compare"}</p><MacroMetricCell metric={summary?.yoy} locale={locale} signed /></div><div><p className="font-data text-[7px] text-agent-dim">{locale === "zh" ? `历史位置 · ${summary?.historical_position?.window || "10Y"}` : `History · ${summary?.historical_position?.window || "10Y"}`}</p><MacroMetricCell metric={summary?.historical_position} locale={locale} percentile /></div></div><div className="mt-2 flex items-end gap-3"><div className="h-7 flex-1">{sparkline.length > 1 ? <MiniLine values={sparkline} color="var(--agent-blue)" height={30} /> : null}</div><span className="font-data text-[7px] text-agent-dim">{row.end || "—"}</span></div></button> : <><div className="flex items-start justify-between gap-2"><div><p className="text-[11px] text-agent-text">{macroLabel(row.key, locale)}</p><p className="mt-1 font-data text-[8px] text-agent-dim">{macroSourceNote(row, locale)}</p></div></div><p className="mt-4 text-[9px] leading-4 text-agent-amber">{row.reason || (locale === "zh" ? "数据未接入" : "Not integrated")}</p></>}
    {row.available && featured.length ? <div className="mt-3 border-t border-agent-border pt-2"><p className="mb-1.5 font-data text-[7px] tracking-[.14em] text-agent-dim">{locale === "zh" ? "结构快照" : "STRUCTURE SNAPSHOT"}</p><div className={cn("grid gap-1", featured.length === 2 ? "grid-cols-2" : "grid-cols-3")}>{featured.map(field => <button type="button" key={field.key} onClick={() => onOpenField(field.key)} className="rounded-sm border border-agent-border/70 bg-agent-raised/40 px-2 py-1.5 text-left hover:border-agent-mint/60 hover:bg-agent-raised focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-agent-mint"><span className="block truncate text-[8px] text-agent-dim">{field.label}</span><span className="mt-0.5 block font-data text-[10px] text-agent-text">{formatMacroFieldValue(field.value, field.unit)}</span></button>)}</div></div> : null}
    {row.available && (featured.length || row.domain === "rates") ? <button type="button" onClick={onOpenAll} className="mt-2 rounded-sm font-data text-[8px] text-agent-blue hover:text-agent-mint focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-agent-mint">{row.domain === "rates" ? (locale === "zh" ? "进入完整利率工作台 →" : "Open rates workspace →") : (locale === "zh" ? `查看全部 ${row.field_catalog?.length || row.fields.length} 项 →` : `View all ${row.field_catalog?.length || row.fields.length} fields →`)}</button> : null}
  </article>;
}

export function macroLabel(key: string, locale: "zh" | "en") { const labels: Record<string, [string, string]> = { gdp: ["GDP 同比", "GDP YoY"], cpi: ["CPI 同比", "CPI YoY"], ppi: ["PPI 同比", "PPI YoY"], money_supply: ["M2 同比", "M2 YoY"], social_financing: ["社会融资增量", "Social Financing Flow"], pmi: ["制造业 PMI", "Manufacturing PMI"], industrial_production_yoy: ["工业增加值同比", "Industrial Production YoY"], retail_sales_yoy: ["社会消费品零售同比", "Retail Sales YoY"], fixed_asset_investment_ytd_yoy: ["固定资产投资累计同比", "Fixed Asset Investment YTD YoY"], urban_unemployment_rate: ["城镇调查失业率", "Urban Unemployment"], exports_usd_yoy: ["出口同比（美元）", "Exports YoY (USD)"], imports_usd_yoy: ["进口同比（美元）", "Imports YoY (USD)"], trade_balance_usd: ["贸易差额", "Trade Balance"], fx_reserves_usd: ["外汇储备", "FX Reserves"], new_rmb_loans: ["新增人民币贷款", "New RMB Loans"], fiscal: ["财政收支", "Fiscal Revenue & Expenditure"], shibor: ["上海银行间同业拆放利率", "SHIBOR"], lpr: ["贷款市场报价利率", "LPR"], us_treasury: ["美国国债收益率", "US Treasury"], us_real_treasury: ["美国实际国债收益率", "US Real Treasury"] }; return labels[key]?.[locale === "zh" ? 0 : 1] || key; }

export function macroSourceNote(row: MacroCatalog["items"][number], locale: "zh" | "en") { const stale = row.quality?.freshness_state === "stale" ? (locale === "zh" ? ` · 已滞后 ${row.quality.lag_days || 0} 天` : ` · stale by ${row.quality.lag_days || 0} days`) : ""; if (row.quality?.source_type === "eco_cal_gated") return (locale === "zh" ? `Tushare eco_cal · 覆盖门禁 ${row.quality.coverage_points || 0}/${row.quality.minimum_samples || 0}` : `Tushare eco_cal · coverage gate ${row.quality.coverage_points || 0}/${row.quality.minimum_samples || 0}`) + stale; if (row.quality?.source_type === "unavailable") return locale === "zh" ? "未接入 · 不使用代理" : "Not integrated · no proxy"; return (locale === "zh" ? `Tushare 结构化 · ${row.source || row.table || "—"}` : `Structured Tushare · ${row.source || row.table || "—"}`) + stale; }

function MacroMetricCell({ metric, locale, emphasis = false, signed = false, percentile = false }: { metric?: MacroMetricSummary; locale: "zh" | "en"; emphasis?: boolean; signed?: boolean; percentile?: boolean }) {
  const value = formatMacroMetric(metric, locale, signed, percentile);
  const method = metric?.method === "official" ? (locale === "zh" ? "官" : "OFF") : metric?.method === "calculated" ? (locale === "zh" ? "算" : "CALC") : null;
  const title = macroMetricExplanation(metric, locale);
  return <span title={title} className={cn("flex items-center justify-end gap-1 text-right font-data", emphasis ? "text-[13px] text-agent-text" : metric?.value != null && Number(metric.value) >= 0 ? "text-agent-muted" : "text-agent-mint")}><span>{value}</span>{method ? <span className={cn("rounded-sm border px-1 py-px text-[7px]", metric?.method === "official" ? "border-agent-blue/30 text-agent-blue" : "border-agent-amber/30 text-agent-amber")}>{method}</span> : null}</span>;
}

function macroSequentialLabel(key: string, locale: "zh" | "en") { if (key === "gdp") return locale === "zh" ? "较上季" : "QoQ change"; if (key === "social_financing" || key === "new_rmb_loans") return locale === "zh" ? "月环比" : "MoM"; return locale === "zh" ? "较上月" : "MoM change"; }

function formatMacroMetric(metric: MacroMetricSummary | undefined, locale: "zh" | "en", signed = false, percentile = false) {
  if (!metric || metric.value == null) return metric?.method === "not_applicable" ? (locale === "zh" ? "不适用" : "N/A") : "—";
  const prefix = signed && metric.value > 0 ? "+" : "";
  const value = new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", { maximumFractionDigits: 2 }).format(metric.value);
  const unit = percentile ? "%" : metric.unit;
  return `${prefix}${value}${unit === "%" || unit === "bp" ? unit : unit ? ` ${unit}` : ""}`;
}

function formatMacroFieldValue(value: number | null, unit: string) {
  if (value == null) return "—";
  const formatted = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value);
  return `${formatted}${unit === "%" || unit === "bp" ? unit : unit ? ` ${unit}` : ""}`;
}

function macroMetricExplanation(metric: MacroMetricSummary | undefined, locale: "zh" | "en") {
  if (!metric) return locale === "zh" ? "等待正式数据。" : "Waiting for formal data.";
  if (metric.method === "not_applicable") return locale === "zh" ? "该口径不适用；不使用代理或反推值。" : "Not applicable; no proxy or inferred value is used.";
  const method = metric.method === "official" ? (locale === "zh" ? "官方" : "Official") : locale === "zh" ? "透明计算" : "Calculated";
  const field = metric.source_field ? `${locale === "zh" ? "字段" : "field"} ${metric.source_field}` : metric.formula || "";
  const sample = metric.sample_count ? ` · ${metric.sample_count} ${locale === "zh" ? "个样本" : "samples"}${metric.window_complete === false ? (locale === "zh" ? `（不足完整${metric.window || "历史"}）` : ` (partial ${metric.window || "history"} window)`) : ""}` : "";
  return `${method}${field ? ` · ${field}` : ""}${sample}`;
}
