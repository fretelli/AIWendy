"use client";

import { FileUp, Plus } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  DashboardPage,
  Donut,
  EmptyPanel,
  MetricCard,
  MissingData,
  Panel,
  SectionTitle,
} from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  agentOSApi,
  type HoldingDetail,
  type PortfolioAccount,
  type PortfolioAnalytics,
  type PortfolioValuation,
} from "@/lib/api/agentos";
import { useUrlTab } from "@/hooks/use-url-tab";
import { useI18n } from "@/lib/i18n/provider";

const COLORS = [
  "var(--agent-mint)",
  "var(--agent-blue)",
  "var(--agent-amber)",
  "var(--agent-up)",
  "#c7a0ff",
  "#8a97a3",
];

type PositionForm = {
  [key: string]: string;
  symbol: string;
  name: string;
  market: string;
  asset_class: string;
  instrument_type: string;
  provider_symbol: string;
  direction: string;
  multiplier: string;
  quantity: string;
  price: string;
  trade_date: string;
  currency: string;
};

export default function HoldingsPage() {
  const { locale, formatCurrency, formatNumber } = useI18n();
  const [tab, setTab] = useUrlTab(["detail", "hedge"], "detail");
  const [accounts, setAccounts] = useState<PortfolioAccount[]>([]);
  const [accountId, setAccountId] = useState<string>("");
  const [valuation, setValuation] = useState<PortfolioValuation | null>(null);
  const [transactions, setTransactions] = useState<
    Array<Record<string, unknown>>
  >([]);
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [detail, setDetail] = useState<HoldingDetail | null>(null);
  const [positionOpen, setPositionOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<PositionForm>({
    symbol: "",
    name: "",
    market: "CN",
    asset_class: "stock",
    instrument_type: "stock",
    provider_symbol: "",
    direction: "long",
    multiplier: "1",
    quantity: "",
    price: "",
    trade_date: new Date().toISOString().slice(0, 10),
    currency: "CNY",
  });
  const loadAccounts = async () => {
    const result = await agentOSApi.accounts();
    setAccounts(result.items);
    setAccountId((current) => current || result.items[0]?.id || "");
  };
  const loadAccount = async (id: string) => {
    const [value, flows, nextAnalytics] = await Promise.all([
      agentOSApi.valuation(id),
      agentOSApi.transactions(id),
      agentOSApi.analytics(id),
    ]);
    setValuation(value);
    setTransactions(flows.items);
    setAnalytics(nextAnalytics);
  };
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const result = await agentOSApi.accounts();
      if (cancelled) return;
      setAccounts(result.items);
      setAccountId((current) => current || result.items[0]?.id || "");
    })().catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    if (!accountId) return;
    let cancelled = false;
    void (async () => {
      const [value, flows, nextAnalytics] = await Promise.all([
        agentOSApi.valuation(accountId),
        agentOSApi.transactions(accountId),
        agentOSApi.analytics(accountId),
      ]);
      if (cancelled) return;
      setValuation(value);
      setTransactions(flows.items);
      setAnalytics(nextAnalytics);
    })().catch(() => {
      if (!cancelled) setValuation(null);
    });
    return () => {
      cancelled = true;
    };
  }, [accountId]);
  const byAsset = useMemo(() => {
    const result = new Map<string, number>();
    for (const item of valuation?.positions ?? []) {
      const key = item.instrument_type || item.asset_class;
      result.set(key, (result.get(key) || 0) + (item.market_value || 0));
    }
    return [...result.entries()].map(([key, value]) => ({ key, value }));
  }, [valuation]);
  const createAccount = async () => {
    const account = await agentOSApi.createAccount({
      name: locale === "zh" ? "我的投资组合" : "My Portfolio",
      base_currency: "CNY",
    });
    await loadAccounts();
    setAccountId(account.id);
  };
  const savePosition = async (event: FormEvent) => {
    event.preventDefault();
    if (!accountId) return;
    setSaving(true);
    try {
      await agentOSApi.addTransaction(accountId, {
        ...form,
        transaction_type: "opening",
        quantity: Number(form.quantity),
        price: Number(form.price),
        manual_price: Number(form.price),
        multiplier: Number(form.multiplier),
        cash_amount: 0,
      });
      setPositionOpen(false);
      await loadAccount(accountId);
      toast.success(
        locale === "zh"
          ? "持仓已记入不可变账本"
          : "Position added to the immutable ledger",
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };
  return (
    <DashboardPage>
      <div className="flex flex-wrap items-center gap-2">
        {accounts.length ? (
          <Select value={accountId} onValueChange={setAccountId}>
            <SelectTrigger className="w-[220px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {accounts.map((account) => (
                  <SelectItem key={account.id} value={account.id}>
                    {account.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        ) : null}
        <div className="ml-auto flex gap-2">
          <Button
            variant="outline"
            onClick={() => setImportOpen(true)}
            disabled={!accountId}
          >
            <FileUp />
            {locale === "zh" ? "导入 CSV" : "Import CSV"}
          </Button>
          <Button onClick={() => setPositionOpen(true)} disabled={!accountId}>
            <Plus />
            {locale === "zh" ? "记录持仓" : "Add position"}
          </Button>
        </div>
      </div>
      {!accounts.length ? (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {[
              locale === "zh" ? "持仓市值" : "Market value",
              locale === "zh" ? "累计浮动盈亏" : "Total P&L",
              locale === "zh" ? "今日盈亏" : "Today P&L",
              locale === "zh" ? "现金" : "Cash",
              locale === "zh" ? "组合波动率" : "Portfolio volatility",
            ].map((label) => <MetricCard key={label} label={label} value="—" note={locale === "zh" ? "等待真实组合数据" : "Waiting for real portfolio data"} />)}
          </div>
          <Panel>
            <EmptyPanel
              title={locale === "zh" ? "建立真实组合账本" : "Create a real portfolio ledger"}
              detail={locale === "zh" ? "KeelTrader 不连接券商。请创建账户后手工录入，或导入持仓、流水和历史净值 CSV。" : "KeelTrader does not connect to brokers. Create an account, then add data manually or import CSV."}
              action={locale === "zh" ? "创建组合账户" : "Create account"}
              onAction={() => void createAccount()}
            />
          </Panel>
          <div className="grid gap-3 xl:grid-cols-[1fr_320px]">
            <Panel className="min-h-[240px]"><SectionTitle title={locale === "zh" ? "持仓明细" : "Position Details"} /><EmptyPanel title={locale === "zh" ? "组合为空" : "Portfolio is empty"} detail={locale === "zh" ? "创建组合后，手工记录持仓或导入 CSV。" : "Create a portfolio, then add positions manually or import CSV."} /></Panel>
            <Panel className="min-h-[240px]"><SectionTitle title={locale === "zh" ? "市值与风险贡献" : "Value & Risk Contribution"} /><EmptyPanel title={locale === "zh" ? "风险贡献不可用" : "Risk contribution unavailable"} detail={locale === "zh" ? "没有正式持仓和收益历史时保持空缺，不按示例权重或市值代理合成。" : "Without formal positions and return history, this remains blank; no sample weights or market-value proxy is substituted."} /></Panel>
          </div>
        </>
      ) : (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <MetricCard
              label={locale === "zh" ? "持仓市值" : "MARKET VALUE"}
              value={
                valuation
                  ? formatCurrency(
                      valuation.total_value,
                      valuation.base_currency,
                    )
                  : "—"
              }
              note={valuation?.as_of}
              color="text-agent-up"
            />
            <MetricCard
              label={locale === "zh" ? "累计浮动盈亏" : "TOTAL P&L"}
              value={
                valuation
                  ? formatCurrency(
                      valuation.positions.reduce(
                        (sum, item) => sum + (item.unrealized_pnl || 0),
                        0,
                      ),
                      valuation.base_currency,
                    )
                  : "—"
              }
              note={
                locale === "zh"
                  ? "按最新可用正式价格"
                  : "Latest available formal prices"
              }
              color={
                valuation &&
                valuation.positions.reduce(
                  (sum, item) => sum + (item.unrealized_pnl || 0),
                  0,
                ) >= 0
                  ? "text-agent-up"
                  : "text-agent-down"
              }
            />
            <MetricCard
              label={locale === "zh" ? "今日盈亏" : "TODAY P&L"}
              value={
                analytics?.today_pnl.value != null
                  ? formatCurrency(
                      analytics.today_pnl.value,
                      valuation?.base_currency || "CNY",
                    )
                  : "—"
              }
              note={analytics?.today_pnl.as_of || analytics?.today_pnl.reason}
              color={
                (analytics?.today_pnl.value || 0) >= 0
                  ? "text-agent-up"
                  : "text-agent-down"
              }
            />
            <MetricCard
              label={locale === "zh" ? "现金" : "CASH"}
              value={
                analytics?.cash.value != null
                  ? formatCurrency(
                      analytics.cash.value,
                      valuation?.base_currency || "CNY",
                    )
                  : "—"
              }
              note={`${transactions.length} ${locale === "zh" ? "条不可变流水" : "immutable entries"}`}
              color="text-agent-blue"
            />
            <MetricCard
              label={locale === "zh" ? "组合波动率" : "PORTFOLIO VOLATILITY"}
              value={
                analytics?.volatility.value != null
                  ? `${(analytics.volatility.value * 100).toFixed(1)}%`
                  : "—"
              }
              note={
                analytics?.volatility.reason ||
                `${analytics?.volatility.observations || 0} ${locale === "zh" ? "个观测值" : "observations"}`
              }
              color="text-agent-amber"
            />
          </div>
          {valuation ? <MissingData items={valuation.missing} /> : null}
          <Tabs
            value={tab}
            onValueChange={setTab}
            className="flex flex-col gap-3"
          >
            <TabsList className="h-auto w-fit border border-agent-border bg-agent-chrome p-1 lg:hidden">
              <TabsTrigger value="detail">
                {locale === "zh" ? "持仓明细" : "Positions"}
              </TabsTrigger>
              <TabsTrigger value="hedge">
                {locale === "zh" ? "对冲与衍生品" : "Hedge & Derivatives"}
              </TabsTrigger>
            </TabsList>
            <TabsContent
              value="detail"
              className="mt-0 grid gap-3 xl:grid-cols-[1fr_320px]"
            >
              <Panel className="order-2 flex min-h-[340px] flex-col xl:order-2">
                <SectionTitle
                  title={
                    locale === "zh"
                      ? "按大类 · 市值与风险贡献"
                      : "Asset Class · Value & Risk Contribution"
                  }
                  en="LIVE HOLDINGS"
                />
                {byAsset.length ? (
                  <>
                    <div className="w-full divide-y divide-agent-border">
                      {byAsset.map((item, index) => (
                        <div
                          key={item.key}
                          className="flex items-center gap-2 py-2 text-[10px]"
                        >
                          <span
                            className="size-2 rounded-full"
                            style={{
                              backgroundColor: COLORS[index % COLORS.length],
                            }}
                          />
                          <span className="flex-1 text-agent-muted">
                            {item.key}
                          </span>
                          <span className="font-data text-agent-text">
                            {formatCurrency(
                              item.value,
                              valuation?.base_currency || "CNY",
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-5 w-full border-t border-agent-border pt-4">
                      <p className="text-xs text-agent-text">
                        {locale === "zh" ? "标的详情" : "INSTRUMENT DETAILS"}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(valuation?.positions || []).map((item) => (
                          <Button
                            key={item.instrument_id}
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              void agentOSApi
                                .holdingDetail(accountId, item.instrument_id)
                                .then(setDetail)
                                .catch((error) =>
                                  toast.error(
                                    error instanceof Error
                                      ? error.message
                                      : "Detail unavailable",
                                  ),
                                )
                            }
                          >
                            {item.name}
                          </Button>
                        ))}
                      </div>
                    </div>
                    <p className="mt-5 text-[10px] leading-5 text-agent-dim">
                      {analytics?.risk_contribution.reason ||
                        (locale === "zh"
                          ? "风险贡献仅在正式历史满足门槛时显示；缺失时不按市值合成。"
                          : "Risk contribution is shown only when formal history meets the threshold; market-value proxies are not substituted.")}
                    </p>
                  </>
                ) : (
                  <EmptyPanel
                    title={locale === "zh" ? "没有持仓" : "No positions"}
                    detail={
                      locale === "zh"
                        ? "记录第一项持仓或导入 CSV。"
                        : "Add the first position or import CSV."
                    }
                  />
                )}
              </Panel>
              <Panel className="order-1 overflow-hidden p-0 xl:order-1">
                <div className="p-4">
                  <SectionTitle
                    title={locale === "zh" ? "持仓明细" : "Position Details"}
                    en="COST / PRICE / RISK"
                  />
                </div>
                {valuation?.positions.length ? (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[820px] text-left text-[10px]">
                      <thead className="border-y border-agent-border bg-agent-chrome font-data text-agent-dim">
                        <tr>
                          <th className="px-4 py-2 font-normal">
                            {locale === "zh" ? "标的" : "Instrument"}
                          </th>
                          <th className="px-3 py-2 font-normal">
                            {locale === "zh" ? "数量" : "Quantity"}
                          </th>
                          <th className="px-3 py-2 font-normal">
                            {locale === "zh" ? "成本" : "Cost"}
                          </th>
                          <th className="px-3 py-2 font-normal">
                            {locale === "zh" ? "价格" : "Price"}
                          </th>
                          <th className="px-3 py-2 font-normal">
                            {locale === "zh" ? "市值" : "Market value"}
                          </th>
                          <th className="px-3 py-2 font-normal">
                            {locale === "zh" ? "浮动盈亏" : "P&L"}
                          </th>
                          <th className="px-3 py-2 font-normal">
                            {locale === "zh" ? "来源 / 日期" : "SOURCE / AS OF"}
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-agent-border">
                        {valuation.positions.map((item) => (
                          <tr
                            key={item.instrument_id}
                            className="hover:bg-agent-raised"
                          >
                            <td className="px-4 py-3">
                              <span className="block text-xs text-agent-text">
                                {item.name}
                              </span>
                              <span className="font-data text-[9px] text-agent-dim">
                                {item.symbol} ·{" "}
                                {item.instrument_type || item.asset_class} ·{" "}
                                {item.direction}
                              </span>
                            </td>
                            <td className="px-3 py-3 font-data text-agent-muted">
                              {formatNumber(item.quantity)}
                            </td>
                            <td className="px-3 py-3 font-data text-agent-muted">
                              {item.average_cost
                                ? formatNumber(item.average_cost)
                                : "—"}
                            </td>
                            <td className="px-3 py-3 font-data text-agent-text">
                              {item.price ? formatNumber(item.price) : "—"}
                              <br />
                              <span
                                className={
                                  item.price_status === "current"
                                    ? "text-agent-mint"
                                    : item.price_status === "stale"
                                      ? "text-agent-amber"
                                      : "text-agent-down"
                                }
                              >
                                {item.price_status || "unavailable"}
                              </span>
                            </td>
                            <td className="px-3 py-3 font-data text-agent-text">
                              {item.market_value !== undefined
                                ? formatCurrency(
                                    item.market_value,
                                    item.currency,
                                  )
                                : "—"}
                            </td>
                            <td
                              className={`px-3 py-3 font-data ${(item.unrealized_pnl || 0) >= 0 ? "text-agent-up" : "text-agent-down"}`}
                            >
                              {item.unrealized_pnl !== undefined
                                ? formatCurrency(
                                    item.unrealized_pnl,
                                    item.currency,
                                  )
                                : "—"}
                            </td>
                            <td className="px-3 py-3 font-data text-[9px] uppercase text-agent-dim">
                              {item.price_source || "missing"}
                              <br />
                              {item.price_as_of || item.price_date || "—"}
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
                        locale === "zh" ? "组合为空" : "Portfolio is empty"
                      }
                      detail={
                        locale === "zh"
                          ? "生产环境不会自动填入示例持仓。"
                          : "Production never inserts sample positions."
                      }
                    />
                  </div>
                )}
              </Panel>
            </TabsContent>
            <TabsContent value="hedge" className="mt-0">
              <HedgePanel
                valuation={valuation}
                locale={locale}
                formatCurrency={formatCurrency}
              />
            </TabsContent>
          </Tabs>
        </>
      )}
      <PositionDialog
        open={positionOpen}
        setOpen={setPositionOpen}
        form={form}
        setForm={setForm}
        submit={savePosition}
        saving={saving}
        locale={locale}
      />
      <ImportDialog
        open={importOpen}
        setOpen={setImportOpen}
        accountId={accountId}
        reload={() => loadAccount(accountId)}
        locale={locale}
      />
      <HoldingSheet
        detail={detail}
        close={() => setDetail(null)}
        locale={locale}
      />
    </DashboardPage>
  );
}

function HedgePanel({
  valuation,
  locale,
  formatCurrency,
}: {
  valuation: PortfolioValuation | null;
  locale: string;
  formatCurrency: (value: number, currency?: string) => string;
}) {
  const derivatives =
    valuation?.positions.filter((item) =>
      ["future", "futures", "option", "derivative"].includes(
        item.asset_class.toLowerCase(),
      ),
    ) ?? [];
  const equity =
    valuation?.positions
      .filter((item) =>
        ["stock", "equity", "a_stock", "hk_stock", "us_stock"].includes(
          item.asset_class.toLowerCase(),
        ),
      )
      .reduce((sum, item) => sum + (item.market_value || 0), 0) || 0;
  return (
    <div className="grid gap-3 xl:grid-cols-[1fr_.8fr]">
      <Panel>
        <SectionTitle
          title={locale === "zh" ? "衍生品持仓" : "Derivative Positions"}
          en="ACTUAL CONTRACTS"
        />
        {derivatives.length ? (
          <div className="divide-y divide-agent-border">
            {derivatives.map((item) => (
              <div
                key={item.instrument_id}
                className="grid grid-cols-[1fr_100px_120px] py-3 text-xs"
              >
                <span className="text-agent-text">
                  {item.name}
                  <small className="ml-2 font-data text-agent-dim">
                    {item.symbol}
                  </small>
                </span>
                <span className="text-right font-data text-agent-muted">
                  {item.quantity}
                </span>
                <span className="text-right font-data text-agent-text">
                  {item.market_value !== undefined
                    ? formatCurrency(item.market_value, item.currency)
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyPanel
            title={
              locale === "zh" ? "没有衍生品持仓" : "No derivative positions"
            }
            detail={
              locale === "zh"
                ? "不会根据模拟组合给出虚构的对冲成本。录入真实合约后再计算。"
                : "No synthetic hedge cost is shown. Add real contracts before analysis."
            }
          />
        )}
      </Panel>
      <Panel>
        <SectionTitle
          title={locale === "zh" ? "对冲覆盖" : "Hedge Coverage"}
          en="EXPOSURE"
        />
        <div className="rounded-md border border-agent-border bg-agent-raised p-4">
          <p className="font-data text-[9px] text-agent-dim">{locale === "zh" ? "权益敞口" : "EQUITY EXPOSURE"}</p>
          <p className="mt-2 font-data text-2xl text-agent-text">
            {formatCurrency(equity, valuation?.base_currency || "CNY")}
          </p>
          <p className="mt-4 text-[10px] leading-5 text-agent-muted">
            {locale === "zh"
              ? "只有存在真实期货/期权价格、乘数和方向时，系统才计算净 Beta、对冲比例和成本。"
              : "Net beta, hedge ratio, and cost require real derivative prices, multipliers, and directions."}
          </p>
        </div>
      </Panel>
    </div>
  );
}

function HoldingSheet({
  detail,
  close,
  locale,
}: {
  detail: HoldingDetail | null;
  close: () => void;
  locale: string;
}) {
  return (
    <Sheet
      open={Boolean(detail)}
      onOpenChange={(open) => {
        if (!open) close();
      }}
    >
      <SheetContent className="w-full overflow-y-auto border-agent-border bg-agent-chrome text-agent-text sm:max-w-[560px]">
        <SheetHeader>
          <SheetTitle>{detail?.position.name || "—"}</SheetTitle>
          <SheetDescription>
            {detail
              ? `${detail.position.symbol} · ${detail.position.instrument_type} · ${detail.position.price_source || "missing"} · ${detail.position.price_as_of || "—"}`
              : ""}
          </SheetDescription>
        </SheetHeader>
        {detail ? (
          <div className="mt-6 space-y-4">
            <Panel>
              <SectionTitle
                title={locale === "zh" ? "价格历史" : "Price History"}
                en="OFFICIAL SOURCE"
              />
              {detail.history.available ? (
                <div className="max-h-44 overflow-y-auto divide-y divide-agent-border">
                  {detail.history.items
                    .slice(-30)
                    .reverse()
                    .map((item) => (
                      <div
                        key={item.date}
                        className="flex justify-between py-2 font-data text-[10px]"
                      >
                        <span className="text-agent-dim">{item.date}</span>
                        <span>{item.price}</span>
                      </div>
                    ))}
                </div>
              ) : (
                <EmptyPanel
                  title={
                    locale === "zh"
                      ? "价格历史不可用"
                      : "Price history unavailable"
                  }
                  detail={detail.history.reason || "—"}
                />
              )}
            </Panel>
            <Panel>
              <SectionTitle
                title={
                  locale === "zh"
                    ? "财务 / 净值证据"
                    : "Fundamentals / NAV Evidence"
                }
                en="POINT IN TIME"
              />
              {detail.fundamentals.available ? (
                <pre className="max-h-64 overflow-auto whitespace-pre-wrap font-data text-[10px] text-agent-muted">
                  {JSON.stringify(detail.fundamentals.data, null, 2)}
                </pre>
              ) : (
                <EmptyPanel
                  title={
                    locale === "zh"
                      ? "正式证据不可用"
                      : "Formal evidence unavailable"
                  }
                  detail={detail.fundamentals.reason || "—"}
                />
              )}
            </Panel>
            <Panel>
              <SectionTitle
                title={locale === "zh" ? "风险与衍生品" : "Risk & Derivatives"}
                en="NO SYNTHETIC GREEKS"
              />
              <p className="text-xs leading-6 text-agent-muted">
                {detail.derivatives.available
                  ? JSON.stringify(detail.derivatives)
                  : detail.derivatives.reason ||
                    detail.portfolio_context.risk_reason ||
                    (locale === "zh"
                      ? "缺少可审计收益序列、Greeks 或波动率曲面。"
                      : "Auditable returns, Greeks or volatility surface are missing.")}
              </p>
            </Panel>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function PositionDialog({
  open,
  setOpen,
  form,
  setForm,
  submit,
  saving,
  locale,
}: {
  open: boolean;
  setOpen: (value: boolean) => void;
  form: PositionForm;
  setForm: (value: PositionForm) => void;
  submit: (event: FormEvent) => void;
  saving: boolean;
  locale: string;
}) {
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {locale === "zh" ? "记录持仓" : "Add position"}
          </DialogTitle>
          <DialogDescription>
            {locale === "zh"
              ? "必须选择正式标的类型与供应商代码；不能可靠识别时保留 manual。"
              : "Choose an official instrument type and provider symbol; uncertain legacy assets remain manual."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label>{locale === "zh" ? "标的类型" : "Instrument type"}</Label>
              <Select
                value={form.instrument_type}
                onValueChange={(instrument_type) =>
                  setForm({
                    ...form,
                    instrument_type,
                    asset_class: instrument_type,
                  })
                }
              >
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {[
                      "stock",
                      "etf",
                      "open_fund",
                      "future",
                      "option",
                      "convertible_bond",
                      "cash",
                      "fx",
                      "alternative",
                      "manual",
                    ].map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{locale === "zh" ? "方向" : "Direction"}</Label>
              <Select
                value={form.direction}
                onValueChange={(direction) => setForm({ ...form, direction })}
              >
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="long">long</SelectItem>
                  <SelectItem value="short">short</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {[
              ["symbol", "代码 / Symbol"],
              ["provider_symbol", "Provider symbol"],
              ["name", locale === "zh" ? "名称" : "Name"],
              ["quantity", locale === "zh" ? "数量" : "Quantity"],
              ["multiplier", locale === "zh" ? "合约乘数" : "Multiplier"],
              [
                "price",
                locale === "zh" ? "成交 / 手工净值" : "Trade / manual NAV",
              ],
              ["trade_date", locale === "zh" ? "截至日期" : "As of"],
            ].map(([key, label]) => (
              <div key={key} className="flex flex-col gap-1.5">
                <Label htmlFor={`position-${key}`}>{label}</Label>
                <Input
                  id={`position-${key}`}
                  type={
                    ["quantity", "price", "multiplier"].includes(key)
                      ? "number"
                      : key === "trade_date"
                        ? "date"
                        : "text"
                  }
                  step="any"
                  value={form[key]}
                  required={!["provider_symbol"].includes(key)}
                  onChange={(event) =>
                    setForm({ ...form, [key]: event.target.value })
                  }
                />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={saving}>
              {locale === "zh" ? "保存到组合账本" : "Save to ledger"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ImportDialog({
  open,
  setOpen,
  accountId,
  reload,
  locale,
}: {
  open: boolean;
  setOpen: (value: boolean) => void;
  accountId: string;
  reload: () => Promise<void>;
  locale: string;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState("positions");
  const [saving, setSaving] = useState(false);
  const submit = async () => {
    if (!file || !accountId) return;
    setSaving(true);
    try {
      const preview = (await agentOSApi.previewImport({
        account_id: accountId,
        import_type: kind,
        filename: file.name,
        csv_text: await file.text(),
        mapping: {},
      })) as { id: string; errors?: unknown[] };
      if (preview.errors?.length)
        throw new Error(`${preview.errors.length} CSV validation errors`);
      await agentOSApi.commitImport(preview.id);
      await reload();
      setOpen(false);
      toast.success(
        locale === "zh" ? "CSV 已原子导入" : "CSV imported atomically",
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Import failed");
    } finally {
      setSaving(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {locale === "zh" ? "导入组合 CSV" : "Import portfolio CSV"}
          </DialogTitle>
          <DialogDescription>
            {locale === "zh"
              ? "支持 positions、transactions、nav 三种规范字段；先逐行验证，全部通过后单事务提交。"
              : "Supports positions, transactions, and nav fields. Every row is validated before atomic commit."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <Select value={kind} onValueChange={setKind}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="positions">positions</SelectItem>
                <SelectItem value="transactions">transactions</SelectItem>
                <SelectItem value="nav">nav</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
          <Input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <div className="rounded-md border border-agent-border bg-agent-raised p-3 font-data text-[9px] leading-5 text-agent-dim">
            {kind === "positions"
              ? "symbol,name,market,asset_class,quantity,price,currency,as_of"
              : kind === "transactions"
                ? "trade_date,transaction_type,symbol,quantity,price,cash_amount,fee,currency"
                : "snapshot_date,nav,net_flow,currency"}
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => void submit()} disabled={!file || saving}>
            {locale === "zh" ? "验证并导入" : "Validate and import"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
