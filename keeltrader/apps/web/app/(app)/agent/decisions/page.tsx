"use client";

import { FlaskConical, Plus } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  DashboardPage,
  EmptyPanel,
  Panel,
  SectionTitle,
  StatusDot,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  agentOSApi,
  type Decision,
  type StrategyTemplate,
} from "@/lib/api/agentos";
import { useUrlTab } from "@/hooks/use-url-tab";
import { useI18n } from "@/lib/i18n/provider";

function localizeDecisionState(value: string, locale: string) {
  if (locale !== "zh") return value;
  return (
    (
      {
        draft: "草案",
        pending: "待验证",
        confirmed: "成立",
        invalidated: "已失效",
        active: "监测中",
        complete: "已完成",
      } as Record<string, string>
    )[value] || value
  );
}

export default function DecisionsPage() {
  const { locale } = useI18n();
  const [tab, setTab] = useUrlTab(
    ["conditions", "log", "attribution", "strategy"],
    "conditions",
  );
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [experiments, setExperiments] = useState<
    Array<Record<string, unknown>>
  >([]);
  const [decisionOpen, setDecisionOpen] = useState(false);
  const load = async () => {
    const [decisionData, templateData, experimentData] = await Promise.all([
      agentOSApi.decisions(),
      agentOSApi.strategyTemplates(),
      agentOSApi.experiments(),
    ]);
    setDecisions(decisionData.items);
    setTemplates(templateData.items);
    setExperiments(experimentData.items);
  };
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [decisionData, templateData, experimentData] = await Promise.all([
        agentOSApi.decisions(),
        agentOSApi.strategyTemplates(),
        agentOSApi.experiments(),
      ]);
      if (cancelled) return;
      setDecisions(decisionData.items);
      setTemplates(templateData.items);
      setExperiments(experimentData.items);
    })().catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  const conditions = useMemo(
    () =>
      decisions.flatMap((item) =>
        item.conditions.map((condition) => ({ decision: item, condition })),
      ),
    [decisions],
  );
  const confirmed = decisions.filter((item) => item.status === "confirmed");
  const challenged = decisions.filter((item) => item.status === "invalidated");
  return (
    <DashboardPage>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded border border-agent-mint bg-agent-mint/10 px-3 py-2 text-[10px] text-agent-mint">
          {locale === "zh"
            ? `全部条件 ${conditions.length}`
            : `ALL CONDITIONS ${conditions.length}`}
        </span>
        <span className="rounded border border-agent-border px-3 py-2 text-[10px] text-agent-muted">
          {locale === "zh"
            ? `已确认 ${confirmed.length}`
            : `CONFIRMED ${confirmed.length}`}
        </span>
        <span className="rounded border border-agent-border px-3 py-2 text-[10px] text-agent-muted">
          {locale === "zh"
            ? `已失效 ${challenged.length}`
            : `INVALIDATED ${challenged.length}`}
        </span>
        <Button onClick={() => setDecisionOpen(true)}>
          <Plus />
          {locale === "zh" ? "记录新决策" : "New decision"}
        </Button>
      </div>
      <Tabs value={tab} onValueChange={setTab} className="flex flex-col gap-3">
        <TabsList className="h-auto w-fit max-w-full overflow-x-auto border border-agent-border bg-agent-chrome p-1 lg:hidden">
          <TabsTrigger value="conditions">
            {locale === "zh" ? "条件与时机" : "Conditions"}
          </TabsTrigger>
          <TabsTrigger value="log">
            {locale === "zh" ? "决策日志" : "Decision Log"}
          </TabsTrigger>
          <TabsTrigger value="attribution">
            {locale === "zh" ? "收益归因" : "Attribution"}
          </TabsTrigger>
          <TabsTrigger value="strategy">
            {locale === "zh" ? "策略实验室" : "Strategy Lab"}
          </TabsTrigger>
        </TabsList>
        <TabsContent
          value="conditions"
          className="mt-0 grid gap-3 xl:grid-cols-[1fr_280px]"
        >
          <Panel>
            <SectionTitle
              title={
                locale === "zh"
                  ? "每笔决策的可证伪前提"
                  : "Falsifiable Premises"
              }
              en="CONDITIONS / TIMING"
            />
            {conditions.length ? (
              <div className="divide-y divide-agent-border">
                {conditions.map(({ decision, condition }, index) => {
                  const subject = String(
                    condition.subject || condition.metric || decision.title,
                  );
                  const state = String(condition.state || "pending");
                  const statement = String(
                    condition.statement ||
                      condition.condition ||
                      condition.operator ||
                      "—",
                  );
                  const action = String(
                    condition.failure_action || condition.action || "—",
                  );
                  return (
                    <div
                      key={`${decision.id}-${index}`}
                      className="grid gap-2 py-3 md:grid-cols-[160px_1fr_90px_180px]"
                    >
                      <span className="text-xs text-agent-text">
                        {subject}
                        <small className="mt-1 block font-data text-[9px] text-agent-dim">
                          {decision.title}
                        </small>
                      </span>
                      <span className="text-xs leading-5 text-agent-muted">
                        {statement}
                      </span>
                      <span className="flex items-center gap-2 font-data text-[10px] text-agent-amber">
                        <StatusDot status={state} />
                        {localizeDecisionState(state, locale)}
                      </span>
                      <span className="text-[10px] leading-5 text-agent-dim">
                        {action}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <EmptyPanel
                title={
                  locale === "zh" ? "尚无决策条件" : "No decision conditions"
                }
                detail={
                  locale === "zh"
                    ? "决策草案必须补全可验证条件与失效动作后，才适合确认。"
                    : "A draft should define testable conditions and failure actions before confirmation."
                }
              />
            )}
          </Panel>
          <Panel>
            <SectionTitle
              title={locale === "zh" ? "事件日历" : "EVENT CALENDAR"}
            />
            {decisions.some((item) => item.review_date) ? (
              <div className="divide-y divide-agent-border">
                {decisions
                  .filter((item) => item.review_date)
                  .sort((a, b) =>
                    String(a.review_date).localeCompare(String(b.review_date)),
                  )
                  .slice(0, 12)
                  .map((item) => (
                    <div key={item.id} className="py-3">
                      <p className="font-data text-[9px] text-agent-mint">
                        {item.review_date}
                      </p>
                      <p className="mt-1 text-xs text-agent-text">
                        {item.title}
                      </p>
                      <p className="mt-1 text-[10px] text-agent-dim">
                        {localizeDecisionState(item.status, locale)}
                      </p>
                    </div>
                  ))}
              </div>
            ) : (
              <EmptyPanel
                title={locale === "zh" ? "暂无真实事件" : "NO REAL EVENTS"}
                detail={
                  locale === "zh"
                    ? "决策复核日期与正式数据日历会显示在这里。"
                    : "Decision review dates and formal data events appear here."
                }
              />
            )}
          </Panel>
        </TabsContent>
        <TabsContent value="log" className="mt-0">
          <Panel>
            <SectionTitle
              title={
                locale === "zh" ? "不可变决策日志" : "Immutable Decision Log"
              }
              en="RATIONALE / EVIDENCE / REVIEW"
            />
            {decisions.length ? (
              <div className="divide-y divide-agent-border">
                {decisions.map((item) => (
                  <article
                    key={item.id}
                    className="grid gap-3 py-4 lg:grid-cols-[140px_1fr_140px]"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <StatusDot status={item.status} />
                        <span className="font-data text-[10px] uppercase text-agent-muted">
                          {localizeDecisionState(item.status, locale)}
                        </span>
                      </div>
                      <p className="mt-2 font-data text-[9px] text-agent-dim">
                        v{item.current_version} ·{" "}
                        {item.decided_at?.slice(0, 10) ||
                          (locale === "zh" ? "草案" : "DRAFT")}
                      </p>
                    </div>
                    <div>
                      <h3 className="text-sm text-agent-text">{item.title}</h3>
                      <p className="mt-2 text-xs leading-6 text-agent-muted">
                        {item.rationale}
                      </p>
                    </div>
                    <div className="text-[10px] leading-5 text-agent-dim">
                      <p>
                        {item.evidence.length}{" "}
                        {locale === "zh" ? "条证据" : "evidence refs"}
                      </p>
                      <p>
                        {item.conditions.length}{" "}
                        {locale === "zh" ? "项条件" : "conditions"}
                      </p>
                      <p>
                        {item.review_date ||
                          (locale === "zh" ? "无复核日期" : "No review date")}
                      </p>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyPanel
                title={locale === "zh" ? "没有决策记录" : "No decision records"}
                detail={
                  locale === "zh"
                    ? "Agent 可以生成草案，但必须由你确认后才成为正式决策。"
                    : "Agent may draft; only your confirmation creates a formal decision."
                }
              />
            )}
          </Panel>
        </TabsContent>
        <TabsContent
          value="attribution"
          className="mt-0 grid gap-3 xl:grid-cols-[1.2fr_.8fr]"
        >
          <Panel>
            <SectionTitle
              title={
                locale === "zh"
                  ? "历史净值与决策归因"
                  : "NAV & Decision Attribution"
              }
              en="NO PRE-HISTORY METRICS"
            />
            <EmptyPanel
              title={locale === "zh" ? "历史序列不足" : "Insufficient history"}
              detail={
                locale === "zh"
                  ? "导入期初、交易流水或历史净值后，系统才计算 TWR、现金流、费用、汇率和持仓贡献。"
                  : "Import opening data, transactions, or historical NAV before calculating TWR, cash-flow, fee, FX, and position contribution."
              }
            />
          </Panel>
          <Panel>
            <SectionTitle
              title={locale === "zh" ? "三层结算" : "Three-layer Attribution"}
              en="SAA / TAA / SELECTION"
            />
            <EmptyPanel
              title={
                locale === "zh" ? "尚无可归因区间" : "No attributable period"
              }
              detail={
                locale === "zh"
                  ? "只有用户配置有效基准映射并积累真实净值历史后，才显示 SAA、TAA 与标的选择归因。"
                  : "SAA, TAA, and selection attribution appears only after a valid benchmark mapping and real NAV history exist."
              }
            />
          </Panel>
        </TabsContent>
        <TabsContent value="strategy" className="mt-0">
          <StrategyLab
            templates={templates}
            experiments={experiments}
            reload={load}
            locale={locale}
          />
        </TabsContent>
      </Tabs>
      <DecisionDialog
        open={decisionOpen}
        setOpen={setDecisionOpen}
        reload={load}
        locale={locale}
      />
    </DashboardPage>
  );
}

function StrategyLab({
  templates,
  experiments,
  reload,
  locale,
}: {
  templates: StrategyTemplate[];
  experiments: Array<Record<string, unknown>>;
  reload: () => Promise<void>;
  locale: string;
}) {
  const [selected, setSelected] = useState<StrategyTemplate | null>(null);
  const [symbols, setSymbols] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const run = async () => {
    if (!selected) return;
    setRunning(true);
    try {
      const experiment = await agentOSApi.createExperiment({
        name: `${selected.name} ${new Date().toISOString().slice(0, 10)}`,
        template_key: selected.key,
        parameters: {},
      });
      const output = await agentOSApi.runExperiment(String(experiment.id), {
        symbols: symbols.split(/[\s,]+/).filter(Boolean),
        lookback_days: 750,
        top_n: selected.key === "momentum_trend" ? 20 : 30,
        cost_bps: 10,
      });
      setResult(output);
      await reload();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Backtest failed");
    } finally {
      setRunning(false);
    }
  };
  return (
    <div className="grid gap-3 xl:grid-cols-[360px_1fr]">
      <Panel>
        <SectionTitle
          title={locale === "zh" ? "白名单模板" : "Allowlisted Templates"}
          en="VERSIONED FORMULAS"
        />
        <div className="flex flex-col gap-2">
          {templates.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => {
                setSelected(item);
                setResult(null);
              }}
              className={`rounded-md border p-3 text-left ${selected?.key === item.key ? "border-agent-mint bg-agent-mint/5" : "border-agent-border bg-agent-raised"}`}
            >
              <div className="flex items-center gap-2">
                <FlaskConical className="text-agent-mint" />
                <span className="text-xs text-agent-text">
                  {locale === "zh" ? item.name : item.name_en}
                </span>
              </div>
              <p className="mt-2 text-[10px] leading-5 text-agent-dim">
                {item.description}
              </p>
              <p className="mt-2 font-data text-[8px] uppercase text-agent-muted">
                {item.rebalance} · {item.default_cost_bps} BPS
              </p>
            </button>
          ))}
        </div>
      </Panel>
      <Panel>
        <SectionTitle
          title={locale === "zh" ? "真实回测" : "Real Backtest"}
          en="TUSHARE · POINT-IN-TIME"
        />
        {selected ? (
          <div className="flex flex-col gap-4">
            <div>
              <Label htmlFor="strategy-symbols">
                {locale === "zh"
                  ? "股票代码，逗号分隔"
                  : "Symbols, comma separated"}
              </Label>
              <Input
                id="strategy-symbols"
                className="mt-2"
                value={symbols}
                onChange={(event) => setSymbols(event.target.value)}
                placeholder="600519.SH, 601088.SH, 300308.SZ"
              />
            </div>
            {selected.key !== "momentum_trend" ? (
              <div className="rounded-md border border-agent-amber/30 bg-agent-amber/5 p-3 text-[10px] leading-5 text-agent-amber">
                {locale === "zh"
                  ? "红利低波和质量成长还需要请求中提供截至当时的因子值；缺失时回测会明确失败，不回退价格代理。"
                  : "Dividend low-vol and quality growth also require point-in-time factors. Missing factors fail explicitly without price proxies."}
              </div>
            ) : null}
            <Button
              onClick={() => void run()}
              disabled={running || !symbols.trim()}
            >
              {running
                ? locale === "zh"
                  ? "回测中…"
                  : "Running…"
                : locale === "zh"
                  ? "运行不可变版本"
                  : "Run immutable version"}
            </Button>
            {result ? (
              <div className="rounded-md border border-agent-border bg-agent-raised p-4">
                <p
                  className={`font-data text-sm ${result.status === "completed" ? "text-agent-mint" : "text-agent-up"}`}
                >
                  {String(result.status).toUpperCase()}
                </p>
                {result.error_message ? (
                  <p className="mt-3 text-xs text-agent-up">
                    {String(result.error_message)}
                  </p>
                ) : (
                  <pre className="mt-3 overflow-auto font-data text-[10px] leading-5 text-agent-muted">
                    {JSON.stringify(result.metrics, null, 2)}
                  </pre>
                )}
              </div>
            ) : null}
          </div>
        ) : (
          <EmptyPanel
            title={
              locale === "zh" ? "选择策略模板" : "Select a strategy template"
            }
            detail={
              locale === "zh"
                ? "公式、输入数据版本、参数和结果都会随运行版本保存。"
                : "Formula, data version, parameters, and results are persisted with every run."
            }
          />
        )}
      </Panel>
    </div>
  );
}

function DecisionDialog({
  open,
  setOpen,
  reload,
  locale,
}: {
  open: boolean;
  setOpen: (value: boolean) => void;
  reload: () => Promise<void>;
  locale: string;
}) {
  const [form, setForm] = useState({
    title: "",
    rationale: "",
    condition: "",
    failureAction: "",
    review_date: "",
  });
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await agentOSApi.createDecision({
        title: form.title,
        rationale: form.rationale,
        action: {},
        conditions: form.condition
          ? [
              {
                statement: form.condition,
                state: "pending",
                failure_action: form.failureAction,
              },
            ]
          : [],
        evidence: [],
        attribution: {},
        status: "draft",
        review_date: form.review_date || null,
        created_by: "user",
      });
      await reload();
      setOpen(false);
      toast.success(
        locale === "zh" ? "决策草案已保存" : "Decision draft saved",
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {locale === "zh" ? "记录新决策" : "New decision"}
          </DialogTitle>
          <DialogDescription>
            {locale === "zh"
              ? "先保存草案；补全证据和可证伪条件后再确认。"
              : "Save a draft first; confirm after evidence and falsifiable conditions are complete."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div>
            <Label htmlFor="decision-title">
              {locale === "zh" ? "标题" : "Title"}
            </Label>
            <Input
              id="decision-title"
              className="mt-2"
              value={form.title}
              onChange={(event) =>
                setForm({ ...form, title: event.target.value })
              }
              required
            />
          </div>
          <div>
            <Label htmlFor="decision-rationale">
              {locale === "zh" ? "决策理由" : "Rationale"}
            </Label>
            <Textarea
              id="decision-rationale"
              className="mt-2"
              value={form.rationale}
              onChange={(event) =>
                setForm({ ...form, rationale: event.target.value })
              }
              required
            />
          </div>
          <div>
            <Label htmlFor="decision-condition">
              {locale === "zh" ? "可证伪条件" : "Falsifiable condition"}
            </Label>
            <Input
              id="decision-condition"
              className="mt-2"
              value={form.condition}
              onChange={(event) =>
                setForm({ ...form, condition: event.target.value })
              }
            />
          </div>
          <div>
            <Label htmlFor="decision-action">
              {locale === "zh" ? "条件失效动作" : "Failure action"}
            </Label>
            <Input
              id="decision-action"
              className="mt-2"
              value={form.failureAction}
              onChange={(event) =>
                setForm({ ...form, failureAction: event.target.value })
              }
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={saving}>
              {locale === "zh" ? "保存草案" : "Save draft"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
