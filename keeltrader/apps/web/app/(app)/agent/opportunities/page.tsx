"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  DashboardPage,
  EmptyPanel,
  Panel,
  SectionTitle,
  StatusDot,
} from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUrlTab } from "@/hooks/use-url-tab";
import {
  agentPlatformApi,
  marketsApi,
  type HolderInboxEvent,
  type HolderWatchItem,
  type Opportunity,
} from "@/lib/api/agent-platform";
import { useI18n } from "@/lib/i18n/provider";

export default function OpportunitiesPage() {
  const { locale } = useI18n();
  const [tab, setTab] = useUrlTab(["signals", "relative"], "signals", {
    people: "signals",
  });
  const [items, setItems] = useState<Opportunity[]>([]);
  const [holders, setHolders] = useState<HolderWatchItem[]>([]);
  const [events, setEvents] = useState<HolderInboxEvent[]>([]);
  const load = async () => {
    const [feed, watch, changes] = await Promise.all([
      marketsApi.opportunities({ limit: 100, offset: 0 }),
      agentPlatformApi.holderWatchlist(),
      agentPlatformApi.holderEvents(false),
    ]);
    setItems(feed.items);
    setHolders(watch.items);
    setEvents(changes.items);
  };
  useEffect(() => {
    void (async () => {
      await load();
    })().catch(() => undefined);
  }, []);
  const signals = items.filter((item) =>
    ["company", "holder", "macro", "capital"].includes(item.domain),
  );
  const relative = items.filter((item) =>
    ["rates", "futures", "options"].includes(item.domain),
  );
  const active = items.filter((item) =>
    ["new", "active", "changed", "challenged"].includes(item.state),
  );
  const follow = async (item: Opportunity) => {
    try {
      await marketsApi.followOpportunity(item.id, {
        state: "following",
        notes:
          "Research record created from Opportunity Center; no order execution.",
      });
      await load();
      toast.success(
        locale === "zh"
          ? "已创建研究跟踪记录"
          : "Research tracking record created",
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Follow failed");
    }
  };
  return (
    <DashboardPage>
      <div className="flex flex-wrap items-center gap-2 text-[10px]">
        <span className="rounded border border-agent-mint bg-agent-mint/10 px-3 py-2 text-agent-mint">
          {locale === "zh"
            ? `全部信号 ${items.length}`
            : `ALL SIGNALS ${items.length}`}
        </span>
        <span className="rounded border border-agent-border px-3 py-2 text-agent-muted">
          {locale === "zh"
            ? `活跃 ${active.length}`
            : `ACTIVE ${active.length}`}
        </span>
        <span className="rounded border border-agent-border px-3 py-2 text-agent-muted">
          {locale === "zh"
            ? `跟踪人物与机构 ${holders.length}`
            : `TRACKED ENTITIES ${holders.length}`}
        </span>
        <span className="rounded border border-agent-border px-3 py-2 text-agent-muted">
          {locale === "zh"
            ? `相对价值 ${relative.length}`
            : `RELATIVE VALUE ${relative.length}`}
        </span>
        <span className="ml-auto font-data text-agent-dim">
          {locale === "zh"
            ? "按与组合的可审计相关性排序"
            : "SORTED BY AUDITABLE PORTFOLIO RELEVANCE"}
        </span>
      </div>
      <Tabs value={tab} onValueChange={setTab} className="flex flex-col gap-3">
        <TabsList className="h-auto w-fit border border-agent-border bg-agent-chrome p-1 lg:hidden">
          <TabsTrigger value="signals">
            {locale === "zh" ? "信号" : "Signals"}
          </TabsTrigger>
          <TabsTrigger value="relative">
            {locale === "zh" ? "相对价值" : "Relative Value"}
          </TabsTrigger>
        </TabsList>
        <TabsContent
          value="signals"
          className="mt-0 grid gap-3 xl:grid-cols-[1fr_320px]"
        >
          <OpportunityTable items={signals} locale={locale} onFollow={follow} />
          <div className="grid content-start gap-3">
            <Panel>
              <SectionTitle
                title={
                  locale === "zh" ? "跟踪人物 / 机构" : "People & Institutions"
                }
                en="DISCLOSURE WATCH"
              />
              {holders.length ? (
                <div className="divide-y divide-agent-border">
                  {holders.map((item) => (
                    <div key={item.id} className="py-3">
                      <div className="flex items-center gap-2">
                        <StatusDot
                          status={item.enabled ? "active" : "unavailable"}
                        />
                        <span className="text-xs text-agent-text">
                          {item.holder_name}
                        </span>
                        <span className="ml-auto font-data text-[9px] text-agent-dim">
                          {item.holder_type}
                        </span>
                      </div>
                      {item.identity_warning ? (
                        <p className="mt-2 text-[10px] text-agent-amber">
                          {item.identity_warning}
                        </p>
                      ) : null}
                      <p className="mt-1 font-data text-[9px] text-agent-dim">
                        {item.last_scanned_at ||
                          (locale === "zh" ? "等待扫描" : "AWAITING SCAN")}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyPanel
                  title={
                    locale === "zh" ? "没有跟踪对象" : "No tracked entities"
                  }
                  detail={
                    locale === "zh"
                      ? "确认股东身份后才可加入跟踪。"
                      : "Holder identity must be confirmed first."
                  }
                />
              )}
            </Panel>
            <Panel>
              <SectionTitle
                title={locale === "zh" ? "最新披露变化" : "Latest Disclosures"}
                en="FORMAL SOURCES"
              />
              {events.length ? (
                <div className="divide-y divide-agent-border">
                  {events.slice(0, 8).map((item) => (
                    <div key={item.id} className="py-3">
                      <p className="text-xs text-agent-text">
                        {item.holder_name} · {item.company_name || item.ts_code}
                      </p>
                      <p className="mt-1 font-data text-[9px] text-agent-dim">
                        {item.event_type} · {item.ann_date || item.end_date}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyPanel
                  title={locale === "zh" ? "暂无变化" : "No changes"}
                  detail={
                    locale === "zh"
                      ? "只使用正式披露，不用传闻补位。"
                      : "Formal disclosures only."
                  }
                />
              )}
            </Panel>
          </div>
        </TabsContent>
        <TabsContent
          value="relative"
          className="mt-0 grid gap-3 xl:grid-cols-[1fr_320px]"
        >
          <OpportunityTable
            items={relative}
            locale={locale}
            onFollow={follow}
          />
          <Panel>
            <SectionTitle
              title={locale === "zh" ? "执行可行性" : "Execution Feasibility"}
              en="RESEARCH ONLY"
            />
            <div className="space-y-3 text-xs leading-6 text-agent-muted">
              <p>
                {locale === "zh"
                  ? "每条相对价值机会必须同时说明期限结构或基差、IV/RV、流动性、保证金与失效条件。"
                  : "Every relative-value item must disclose term structure or basis, IV/RV, liquidity, margin and falsifiers."}
              </p>
              <div className="rounded border border-agent-border bg-agent-raised p-3 text-agent-amber">
                {locale === "zh"
                  ? "跟踪仅创建研究记录；不连接券商、不生成订单。"
                  : "Following creates a research record only; no broker or orders."}
              </div>
              <div className="rounded border border-agent-border bg-agent-raised p-3">
                <p className="font-data text-[9px] text-agent-dim">{locale === "zh" ? "数据缺口" : "DATA GAPS"}</p>
                <p className="mt-2">
                  {locale === "zh"
                    ? "缺少可靠期限结构或波动率曲面时，机会保持不可用。"
                    : "Items remain unavailable without reliable curves or volatility surfaces."}
                </p>
              </div>
            </div>
          </Panel>
        </TabsContent>
      </Tabs>
    </DashboardPage>
  );
}

function OpportunityTable({
  items,
  locale,
  onFollow,
}: {
  items: Opportunity[];
  locale: string;
  onFollow: (item: Opportunity) => Promise<void>;
}) {
  const sorted = useMemo(
    () =>
      [...items].sort((a, b) => b.last_seen_at.localeCompare(a.last_seen_at)),
    [items],
  );
  return (
    <Panel className="overflow-hidden p-0">
      <div className="p-4">
        <SectionTitle
          title={
            locale === "zh"
              ? "组合相关的可审计发现"
              : "Portfolio-relevant Findings"
          }
          en="TRIGGER / EVIDENCE / FALSIFIER"
        />
      </div>
      {sorted.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-[10px]">
            <thead className="border-y border-agent-border bg-agent-chrome font-data text-agent-dim">
              <tr>
                <th className="px-4 py-2 font-normal">
                  {locale === "zh" ? "领域" : "DOMAIN"}
                </th>
                <th className="px-3 py-2 font-normal">
                  {locale === "zh"
                    ? "信号与组合关联"
                    : "Signal & Portfolio Link"}
                </th>
                <th className="px-3 py-2 font-normal">
                  {locale === "zh" ? "状态" : "STATE"}
                </th>
                <th className="px-3 py-2 font-normal">
                  {locale === "zh" ? "截至" : "AS OF"}
                </th>
                <th className="px-3 py-2 font-normal">
                  {locale === "zh" ? "证伪条件" : "Falsifier"}
                </th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-agent-border">
              {sorted.map((item) => (
                <tr key={item.id} className="hover:bg-agent-raised">
                  <td className="px-4 py-3 font-data uppercase text-agent-mint">
                    {localizeDomain(item.domain, locale)}
                  </td>
                  <td className="max-w-[420px] px-3 py-3">
                    <p className="text-xs text-agent-text">{localizedOpportunityText(item, locale).title}</p>
                    <p className="mt-1 line-clamp-2 text-agent-dim">
                      {localizedOpportunityText(item, locale).hypothesis}
                    </p>
                  </td>
                  <td className="px-3 py-3 font-data text-agent-muted">
                    {localizeState(item.state, locale)}
                  </td>
                  <td className="px-3 py-3 font-data text-agent-dim">
                    {item.as_of || "—"}
                  </td>
                  <td className="max-w-[220px] px-3 py-3 text-agent-muted">
                    {localizedOpportunityText(item, locale).falsifier}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={item.followed}
                      onClick={() => void onFollow(item)}
                    >
                      {item.followed
                        ? locale === "zh"
                          ? "已跟踪"
                          : "Following"
                        : locale === "zh"
                          ? "跟踪"
                          : "Follow"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-4">
          <EmptyPanel
            title={
              locale === "zh" ? "没有合格机会" : "No qualified opportunities"
            }
            detail={
              locale === "zh"
                ? "机会必须具备触发、来源日期、证据和证伪条件。"
                : "Trigger, dated sources, evidence and falsifiers are required."
            }
          />
        </div>
      )}
    </Panel>
  );
}

function localizeDomain(value: string, locale: string) {
  if (locale !== "zh") return value;
  return (
    (
      {
        company: "公司",
        holder: "股东",
        macro: "宏观",
        capital: "资金",
        rates: "利率",
        futures: "期货",
        options: "期权",
      } as Record<string, string>
    )[value] || value
  );
}

function localizeState(value: string, locale: string) {
  if (locale !== "zh") return value;
  return (
    (
      {
        new: "新发现",
        active: "活跃",
        changed: "已变化",
        challenged: "受挑战",
        invalidated: "已失效",
        following: "跟踪中",
      } as Record<string, string>
    )[value] || value
  );
}

function localizedOpportunityText(item: Opportunity, locale: string) {
  if (locale === "zh") return { title: item.title, hypothesis: item.hypothesis, falsifier: item.falsifiers?.[0] || "—" };
  const playbooks: Record<string, { title: string; hypothesis: string; falsifier: string }> = {
    a_share_capital_participation: { title: "A-share participation, leverage and ETF share changes", hypothesis: "Breadth, financing activity, ETF subscriptions and provider flow data are reviewed as separate evidence and are never merged into a score.", falsifier: "Independent sources diverge, become stale, or conflict with verifiable data." },
    china_liquidity_transmission: { title: "China liquidity transmission to bonds and risk assets", hypothesis: "Repo funding changes may affect Treasury futures before broader risk appetite; only dated confirmations and conflicts are shown.", falsifier: "Repo rates reverse or bond and equity prices do not confirm the move." },
  };
  if (item.playbook_key.startsWith("macro_release_")) return { title: `${item.subject_key.toUpperCase()} latest release and prior-period change`, hypothesis: "The latest formal release may change the growth, inflation or liquidity narrative and requires market-price confirmation.", falsifier: "The source is revised, later data reverses, or asset prices do not confirm it." };
  if (item.playbook_key === "futures_price_open_interest") return { title: `${item.subject_key} main-contract price and open-interest state`, hypothesis: "Price, open interest and contract-roll changes form a structural observation without replacing formal spot or basis data.", falsifier: "Price or open-interest direction reverses, or the underlying relationship cannot be verified." };
  return playbooks[item.playbook_key] || { title: `${localizeDomain(item.domain, locale)} · ${item.subject_key}`, hypothesis: "Review the dated formal evidence for this research signal.", falsifier: "The dated evidence becomes stale, reverses or cannot be verified." };
}
