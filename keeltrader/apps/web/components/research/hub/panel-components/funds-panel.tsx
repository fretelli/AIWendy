"use client";

import { useMemo, useState } from "react";
import { Download, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  trackClientEvent,
  type HedgeFundArchiveFund,
  type HedgeFundArchiveResponse,
  type HedgeFundHoldingsResponse,
} from "@/lib/research-api";

import { formatDateTime, formatUsd } from "../formatters";
import { EmptyState, ErrorState } from "../states";

export function FundsPanel({ archive, holdings, activeFundId, activeMarket, activePeriod, error, onSelectFund, onSelectMarket, onSelectPeriod, onDownloadMiniappCode }: {
  archive: HedgeFundArchiveResponse | null;
  holdings: HedgeFundHoldingsResponse | null;
  activeFundId: string;
  activeMarket: string;
  activePeriod: string;
  error: string;
  onSelectFund: (fund: HedgeFundArchiveFund) => void;
  onSelectMarket: (market: string) => void;
  onSelectPeriod: (period: string) => void;
  onDownloadMiniappCode: (fundId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [regionId, setRegionId] = useState("");
  const [strategyId, setStrategyId] = useState("");
  const [only13f, setOnly13f] = useState(false);
  const [posterStatus, setPosterStatus] = useState("");

  const activeFund = useMemo(() => (archive?.funds || []).find((fund) => fund.id === activeFundId) || null, [archive, activeFundId]);

  function has13fDisclosure(fund: HedgeFundArchiveFund) {
    const filingType = String(fund.latest_filing?.filing_type || "").toLowerCase();
    const sourceName = String(fund.latest_filing?.source_name || "").toLowerCase();
    return filingType.includes("13f") || sourceName.includes("13f");
  }

  const funds = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const raw = archive?.funds || [];
    return raw.filter((fund) => {
      if (regionId && fund.region_id !== regionId) return false;
      if (strategyId && !fund.strategy_ids.includes(strategyId)) return false;
      if (only13f && !has13fDisclosure(fund)) return false;
      if (!normalized) return true;
      return `${fund.name} ${fund.name_zh || ""} ${fund.founder_name} ${fund.core_strategy} ${fund.signature}`.toLowerCase().includes(normalized);
    });
  }, [archive, only13f, query, regionId, strategyId]);

  function resetFilters() {
    setQuery("");
    setRegionId("");
    setStrategyId("");
    setOnly13f(false);
  }

  function escapeSvgText(value: string) {
    return value.replace(/[&<>"']/g, (char) => {
      if (char === "&") return "&amp;";
      if (char === "<") return "&lt;";
      if (char === ">") return "&gt;";
      if (char === '"') return "&quot;";
      return "&apos;";
    });
  }

  function splitPosterLines(value: string, maxChars: number, maxLines: number) {
    const compact = value.trim().replace(/\s+/g, " ");
    const lines: string[] = [];
    for (let index = 0; index < compact.length && lines.length < maxLines; index += maxChars) {
      const next = compact.slice(index, index + maxChars);
      lines.push(index + maxChars < compact.length && lines.length === maxLines - 1 ? `${next.slice(0, Math.max(0, maxChars - 1))}...` : next);
    }
    return lines.length ? lines : ["-"];
  }

  function downloadPoster() {
    if (!activeFund) {
      setPosterStatus("请先选择机构");
      return;
    }
    const topHoldings = (holdings?.holdings || []).slice(0, 8);
    const holdingStartY = 520;
    const height = Math.max(980, holdingStartY + topHoldings.length * 64 + 180);
    const profileLines = splitPosterLines(activeFund.core_strategy || activeFund.latest_dynamic || activeFund.signature || "-", 34, 4);
    const quoteLines = splitPosterLines(activeFund.founder_quote || activeFund.portrait_traits || "-", 34, 3);
    const holdingRows = topHoldings.map((holding, index) => {
      const y = holdingStartY + index * 64;
      const title = escapeSvgText(`${index + 1}. ${holding.security_name || "-"}${holding.ticker ? ` (${holding.ticker})` : ""}`);
      const meta = escapeSvgText(`${formatUsd(holding.market_value_usd)} · ${holding.portfolio_weight ? `${holding.portfolio_weight}%` : "权重 -"}`);
      return `
        <text x="80" y="${y}" font-size="24" font-weight="700" fill="#1f2937">${title}</text>
        <text x="80" y="${y + 30}" font-size="18" fill="#667085">${meta}</text>
      `;
    }).join("");
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="900" height="${height}" viewBox="0 0 900 ${height}">
        <rect width="900" height="${height}" fill="#fbf8ef"/>
        <rect x="42" y="42" width="816" height="${height - 84}" rx="24" fill="#ffffff" stroke="#e6dcc7"/>
        <text x="80" y="118" font-size="22" fill="#8a6b2d">KeelTrader Research · 机构图鉴</text>
        <text x="80" y="182" font-size="44" font-weight="800" fill="#1b4d3e">${escapeSvgText(activeFund.name_zh || activeFund.name)}</text>
        <text x="80" y="224" font-size="24" fill="#667085">${escapeSvgText(activeFund.name)}</text>
        <text x="80" y="282" font-size="22" fill="#1f2937">创始人：${escapeSvgText(activeFund.founder_name || "-")} · ${escapeSvgText(activeFund.founded || "-")}</text>
        <text x="80" y="332" font-size="24" font-weight="700" fill="#1b4d3e">核心策略</text>
        ${profileLines.map((line, index) => `<text x="80" y="${370 + index * 30}" font-size="22" fill="#344054">${escapeSvgText(line)}</text>`).join("")}
        <text x="80" y="470" font-size="20" fill="#8a6b2d">${quoteLines.map(escapeSvgText).join(" ")}</text>
        <text x="80" y="${holdingStartY - 44}" font-size="24" font-weight="700" fill="#1b4d3e">Top 持仓 · ${escapeSvgText(holdings?.selected_period || activePeriod || "最新披露")}</text>
        ${holdingRows || `<text x="80" y="${holdingStartY}" font-size="22" fill="#667085">暂无可展示持仓</text>`}
        <text x="80" y="${height - 96}" font-size="18" fill="#98a2b3">生成时间 ${escapeSvgText(formatDateTime(new Date().toISOString()))} · Web 版长图海报</text>
      </svg>
    `;
    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `hedge-fund-${activeFund.id}-poster.svg`;
    link.click();
    URL.revokeObjectURL(url);
    setPosterStatus("长图海报已生成并下载");
    trackClientEvent({
      event_name: "web_hedge_fund_poster_downloaded",
      page_path: "/research?tab=funds",
      metadata: { fund_id: activeFund.id, market: activeMarket, period: activePeriod || holdings?.selected_period || "" },
    }).catch(() => undefined);
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">机构图鉴</h2>
        <p className="text-sm text-muted-foreground">对应小程序机构图鉴，展示对冲基金档案、策略、创始人与 13F 持仓。</p>
      </div>
      {error ? <ErrorState message={error} /> : null}
      <div className="space-y-3 rounded-md border p-3">
        <div className="flex items-center gap-2 rounded-md border px-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input className="border-0 focus-visible:ring-0" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索机构、创始人、策略" />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant={!regionId ? "secondary" : "outline"} onClick={() => setRegionId("")}>全部地区</Button>
          {(archive?.regions || []).map((region) => (
            <Button key={region.id} size="sm" variant={regionId === region.id ? "secondary" : "outline"} onClick={() => setRegionId(region.id)}>
              {region.display_name || region.name} {region.fund_count ? `· ${region.fund_count}` : ""}
            </Button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant={!strategyId ? "secondary" : "outline"} onClick={() => setStrategyId("")}>全部策略</Button>
          {(archive?.strategies || []).map((strategy) => (
            <Button key={strategy.id} size="sm" variant={strategyId === strategy.id ? "secondary" : "outline"} onClick={() => setStrategyId(strategy.id)}>
              {strategy.name} {strategy.fund_count ? `· ${strategy.fund_count}` : ""}
            </Button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant={only13f ? "secondary" : "outline"} onClick={() => setOnly13f((value) => !value)}>
            仅看 13F 披露
          </Button>
          <Button size="sm" variant="ghost" onClick={resetFilters}>重置筛选</Button>
          <span className="text-sm text-muted-foreground">当前 {funds.length} 家机构</span>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="grid gap-3 md:grid-cols-2">
          {funds.slice(0, 24).map((fund) => (
            <div
              key={fund.id}
              onClick={() => onSelectFund(fund)}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") onSelectFund(fund);
              }}
              className={`cursor-pointer rounded-md border p-4 text-left transition-colors hover:bg-muted/40 ${activeFundId === fund.id ? "border-primary" : ""}`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="font-semibold">{fund.name_zh || fund.name}</div>
                <Badge variant="outline">{fund.logo_text}</Badge>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">{fund.name}</div>
              <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">{fund.latest_dynamic || fund.signature}</p>
              <div className="mt-2 text-xs text-muted-foreground">
                {fund.headquarters || "-"} · {fund.latest_filing?.report_period || "暂无披露期"}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {fund.strategy_names.slice(0, 3).map((strategy) => (
                  <span key={strategy} className="rounded bg-muted px-2 py-1 text-xs text-muted-foreground">
                    {strategy}
                  </span>
                ))}
              </div>
              <div className="mt-3 flex justify-end">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDownloadMiniappCode(fund.id);
                  }}
                >
                  <Download className="mr-2 h-4 w-4" />
                  小程序码
                </Button>
              </div>
            </div>
          ))}
        </div>
        <div className="space-y-4">
        <div className="rounded-md border p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold">机构档案</h3>
              <div className="mt-1 text-sm text-muted-foreground">{activeFund ? `${activeFund.name_zh || activeFund.name} · ${activeFund.headquarters || "-"}` : "选择机构后查看档案"}</div>
            </div>
            {activeFund ? <Badge variant="outline">{activeFund.logo_text}</Badge> : null}
          </div>
          {activeFund ? (
            <div className="mt-3 space-y-3 text-sm">
              <div>
                <div className="font-medium">创始人</div>
                <div className="text-muted-foreground">{activeFund.founder_name || "-"} · {activeFund.founder_title || "-"}</div>
              </div>
              <div>
                <div className="font-medium">画像</div>
                <div className="leading-6 text-muted-foreground">{activeFund.portrait_traits || activeFund.signature || "-"}</div>
              </div>
              <div>
                <div className="font-medium">核心策略</div>
                <div className="leading-6 text-muted-foreground">{activeFund.core_strategy || activeFund.latest_dynamic || "-"}</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={downloadPoster}>
                  <Download className="mr-2 h-4 w-4" />
                  下载长图海报
                </Button>
                <Button size="sm" variant="outline" onClick={() => onDownloadMiniappCode(activeFund.id)}>
                  <Download className="mr-2 h-4 w-4" />
                  小程序码
                </Button>
              </div>
              {posterStatus ? <div className="rounded-md bg-muted/50 p-2 text-xs text-muted-foreground">{posterStatus}</div> : null}
            </div>
          ) : null}
        </div>
        <div className="rounded-md border p-4">
          <h3 className="font-semibold">持仓概览</h3>
          {holdings ? (
            <div className="mt-3 space-y-3">
              <div className="text-sm text-muted-foreground">
                {holdings.fund.name} · {holdings.selected_period || holdings.periods?.[0]?.report_period || "最新披露"}
              </div>
              {holdings.available_markets?.length ? (
                <div className="flex flex-wrap gap-2">
                  {holdings.available_markets.map((market) => (
                    <Button
                      key={market.market}
                      size="sm"
                      variant={(holdings.active_market || activeMarket || "US") === market.market ? "secondary" : "outline"}
                      onClick={() => onSelectMarket(market.market)}
                    >
                      {market.label || market.market} · {market.holding_count}
                    </Button>
                  ))}
                </div>
              ) : null}
              {holdings.periods?.length ? (
                <div className="space-y-2 rounded-md bg-muted/50 p-3">
                  <div className="text-xs text-muted-foreground">可用披露期</div>
                  <div className="flex flex-wrap gap-2">
                    {holdings.periods.slice(0, 8).map((period) => (
                      <Button
                        key={period.report_period}
                        size="sm"
                        variant={(holdings.selected_period || activePeriod) === period.report_period ? "secondary" : "outline"}
                        onClick={() => onSelectPeriod(period.report_period)}
                      >
                        {period.report_period} · {period.holding_count}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}
              {holdings.holdings.slice(0, 10).map((holding, index) => (
                <div key={`${holding.security_name}-${holding.ticker || ""}-${index}`} className="flex items-start justify-between gap-3 border-t pt-3 text-sm">
                  <div>
                    <div className="font-medium">{holding.security_name}</div>
                    <div className="text-xs text-muted-foreground">{holding.ticker || "-"} · {holding.source_name || "13F"}</div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div>{formatUsd(holding.market_value_usd)}</div>
                    <div>{holding.portfolio_weight ? `${holding.portfolio_weight}%` : ""}</div>
                  </div>
                </div>
              ))}
              {!holdings.holdings.length ? <EmptyState title="暂无持仓" description={holdings.coverage_note || "当前机构没有可展示持仓。"} /> : null}
            </div>
          ) : (
            <EmptyState title="选择一个机构" description="点击左侧机构后加载最新持仓。" />
          )}
        </div>
        </div>
      </div>
    </section>
  );
}
