"use client";
import { Loader2 } from "lucide-react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  agentPlatformApi,
  marketsApi,
  type Opportunity,
  type RiskProfile,
  type TradePlan,
} from "@/lib/api/agent-platform";
import { MarketShell } from "../../capital/_components/market-shell";
export default function OpportunitiesPage() {
  const [items, setItems] = useState<Opportunity[]>([]),
    [selected, setSelected] = useState<Opportunity | null>(null),
    [risk, setRisk] = useState<RiskProfile | null>(null),
    [plan, setPlan] = useState<TradePlan | null>(null),
    [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    direction: "",
    instrument: "",
    entry_trigger: "",
    entry_price: "",
    stop_price: "",
    target_price: "",
    horizon: "",
  });
  useEffect(() => {
    Promise.all([marketsApi.opportunities(), agentPlatformApi.riskProfile()])
      .then(([o, r]) => {
        setItems(o.items);
        setRisk(r);
        if (o.items[0]) marketsApi.opportunity(o.items[0].id).then(setSelected);
      })
      .catch((e) =>
        toast.error(e instanceof Error ? e.message : "机会工作区加载失败"),
      )
      .finally(() => setLoading(false));
  }, []);
  const choose = (o: Opportunity) =>
    marketsApi
      .opportunity(o.id)
      .then((v) => {
        setSelected(v);
        setPlan(null);
      })
      .catch((e) => toast.error(String(e)));
  const save = async () => {
    if (risk) {
      setRisk(
        await agentPlatformApi.updateRiskProfile({
          account_equity: risk.account_equity,
        }),
      );
      toast.success("私有风险档案已保存");
    }
  };
  const draft = async () => {
    if (selected)
      setPlan(
        await marketsApi.createTradePlan(selected.id, {
          ...form,
          entry_price: Number(form.entry_price) || undefined,
          stop_price: Number(form.stop_price) || undefined,
          target_price: Number(form.target_price) || undefined,
        }),
      );
  };
  return (
    <MarketShell
      title="跨资产机会"
      subtitle="命名 playbook、正反证据与人工确认交易草案"
      trail={{
        object: selected?.title || "机会流",
        asOf: selected ? Object.values(selected.source_dates)[0] : undefined,
        source: "确定性规则 + 源数据",
      }}
    >
      {loading ? (
        <div className="grid h-80 place-items-center">
          <Loader2 className="h-7 w-7 animate-spin" />
        </div>
      ) : (
        <PanelGroup
          direction="horizontal"
          autoSaveId="opportunity-workspace"
          className="min-h-[calc(100dvh-13rem)] overflow-hidden rounded-xl border bg-card/70"
        >
          <Panel defaultSize={24} minSize={18} maxSize={34}>
            <aside className="h-full overflow-y-auto border-r p-2">
              <p className="px-2 py-3 text-[10px] font-semibold uppercase tracking-[.18em] text-muted-foreground">
                全部观察 · 不评分
              </p>
              {items.map((i) => (
                <button
                  key={i.id}
                  onClick={() => void choose(i)}
                  className={`mb-2 w-full rounded-xl border p-3 text-left ${selected?.id === i.id ? "bg-[hsl(var(--accent)/.12)]" : "bg-background/50 hover:bg-secondary"}`}
                >
                  <span className="block text-xs font-medium">{i.title}</span>
                  <span className="mt-2 block text-[9px] text-muted-foreground">
                    {i.lifecycle_state} ·{" "}
                    {Object.values(i.source_dates).join(" / ")}
                  </span>
                </button>
              ))}
            </aside>
          </Panel>
          <Handle />
          <Panel minSize={38}>
            <main className="h-full overflow-y-auto p-5">
              {selected && (
                <>
                  <h2 className="font-display text-xl font-semibold">
                    {selected.title}
                  </h2>
                  <p className="mt-3 text-sm leading-6">
                    {selected.hypothesis}
                  </p>
                  <div className="mt-5 space-y-3">
                    {selected.evidence?.map((e, n) => (
                      <article
                        key={n}
                        className={`rounded-xl border-l-2 p-4 ${e.stance === "supporting" ? "border-l-emerald-600" : "border-l-amber-600"} border bg-background/60`}
                      >
                        <p className="text-xs leading-5">{e.fact}</p>
                        <p className="mt-2 font-data text-[9px] text-muted-foreground">
                          {e.source} · {e.source_date || "日期不可用"}
                        </p>
                      </article>
                    ))}
                  </div>
                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    <List title="催化剂" items={selected.catalysts} />
                    <List title="证伪条件" items={selected.falsifiers} />
                  </div>
                </>
              )}
            </main>
          </Panel>
          <Handle />
          <Panel defaultSize={30} minSize={24} maxSize={40}>
            <aside className="h-full overflow-y-auto border-l p-4">
              <h2 className="font-display text-lg font-semibold">
                风险与交易草案
              </h2>
              <label className="mt-4 block text-[10px] text-muted-foreground">
                账户权益（仅当前用户私有）
              </label>
              <div className="mt-1 flex gap-2">
                <Input
                  type="number"
                  value={risk?.account_equity ?? ""}
                  onChange={(e) =>
                    risk &&
                    setRisk({
                      ...risk,
                      account_equity: Number(e.target.value) || undefined,
                    })
                  }
                />
                <Button variant="outline" onClick={() => void save()}>
                  保存
                </Button>
              </div>
              <p className="mt-2 text-[9px] text-muted-foreground">
                默认单笔风险 0.5% · 总开放风险 3% · 固定风险法 · 不使用 Kelly
              </p>
              <div className="mt-5 grid gap-2">
                {(Object.keys(labels) as Array<keyof typeof labels>).map(
                  (k) => (
                    <Input
                      key={k}
                      placeholder={labels[k]}
                      type={k.includes("price") ? "number" : "text"}
                      value={form[k]}
                      onChange={(e) =>
                        setForm({ ...form, [k]: e.target.value })
                      }
                    />
                  ),
                )}
              </div>
              <Button className="mt-3 w-full" onClick={() => void draft()}>
                生成待人工确认草案
              </Button>
              {plan && (
                <div className="mt-4 rounded-xl border bg-background/60 p-4 text-xs">
                  <p className="font-semibold">
                    {plan.status === "unavailable"
                      ? "交易计划不可用"
                      : "待人工确认，未连接券商执行"}
                  </p>
                  {plan.unavailable_reason ? (
                    <p className="mt-2 text-muted-foreground">
                      {plan.unavailable_reason}
                    </p>
                  ) : (
                    <div className="mt-2 space-y-1 font-data">
                      <p>数量 {plan.quantity}</p>
                      <p>最大损失 {plan.max_loss}</p>
                      <p>名义金额 {plan.notional}</p>
                    </div>
                  )}
                </div>
              )}
            </aside>
          </Panel>
        </PanelGroup>
      )}
    </MarketShell>
  );
}
const labels = {
  direction: "方向（long / short）",
  instrument: "交易工具",
  entry_trigger: "进场触发条件",
  entry_price: "进场价",
  stop_price: "论点失效止损价",
  target_price: "目标价",
  horizon: "持有期限",
};
const Handle = () => (
  <PanelResizeHandle className="w-1 bg-border/60 hover:bg-[hsl(var(--copper)/.6)]" />
);
function List({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-xl border bg-background/60 p-4">
      <h4 className="text-xs font-semibold">{title}</h4>
      <ul className="mt-2 space-y-2 text-[10px] text-muted-foreground">
        {items.map((i) => (
          <li key={i}>· {i}</li>
        ))}
      </ul>
    </section>
  );
}
