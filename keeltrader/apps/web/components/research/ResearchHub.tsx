"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Bell,
  BookOpen,
  Building2,
  CheckCircle2,
  Gift,
  Heart,
  History,
  Loader2,
  MessageSquare,
  RefreshCw,
  Search,
  Send,
  Settings2,
  Sparkles,
  Star,
  Ticket,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
  dailyCheckIn,
  getBillingOverview,
  getHedgeFundArchive,
  getHedgeFundHoldings,
  getHomeFeed,
  getNotifications,
  getPointsMall,
  getPublicRecommendations,
  getUserProfile,
  redeemPointsMallItem,
  setResearchToken,
  submitFeedback,
  updateUserPreferences,
  type BillingOverview,
  type DigestDetail,
  type HedgeFundArchiveFund,
  type HedgeFundArchiveResponse,
  type HedgeFundHoldingsResponse,
  type NotificationResponse,
  type PointsMallItem,
  type PointsMallResponse,
  type RecommendationResponse,
  type ReportCardItem,
  type UserProfileResponse,
} from "@/lib/research-api";

const FALLBACK_MALL_ITEMS: PointsMallItem[] = [
  {
    code: "book_blind_watchmaker",
    name: "《盲眼钟表匠》",
    subtitle: "[英] 理查德·道金斯，中译版。",
    category: "book",
    points_cost: 20000,
    stock: 1,
    cover_theme: "macro",
    cover_image: "/static/book-blind-watchmaker.png",
    description: "从进化论视角理解复杂生命如何在自然选择中形成。",
    can_redeem: false,
  },
  {
    code: "book_zebra_ulcers",
    name: "《斑马为什么不得胃溃疡》",
    subtitle: "[美] 罗伯特·萨波尔斯基，中译版。",
    category: "book",
    points_cost: 20000,
    stock: 1,
    cover_theme: "value",
    cover_image: "/static/book-zebra-ulcers.png",
    description: "用通俗科学解释压力、身体反应与现代生活的长期损耗。",
    can_redeem: false,
  },
  {
    code: "book_namiya",
    name: "《解忧杂货店》",
    subtitle: "[日] 东野圭吾，中译版。",
    category: "book",
    points_cost: 20000,
    stock: 1,
    cover_theme: "risk",
    cover_image: "/static/book-namiya.png",
    description: "以温柔叙事串起咨询来信、人生选择与迟来的回应。",
    can_redeem: false,
  },
];

const MODULES = [
  { value: "reports", label: "推荐研报", icon: BookOpen },
  { value: "digests", label: "往期期刊", icon: History },
  { value: "funds", label: "机构图鉴", icon: Building2 },
  { value: "mall", label: "积分商城", icon: Gift },
  { value: "membership", label: "权益中心", icon: Ticket },
  { value: "preferences", label: "兴趣设置", icon: Settings2 },
  { value: "feedback", label: "意见反馈", icon: MessageSquare },
] as const;

type TabValue = (typeof MODULES)[number]["value"];

function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${formatDate(value)} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function formatMoneyFen(value?: number | null) {
  return `¥${((value || 0) / 100).toFixed(2)}`;
}

function formatNumber(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("zh-CN");
}

function reportTitle(item: ReportCardItem) {
  return item.display_title || item.title?.replace(/\.pdf$/i, "") || "未命名研报";
}

function imageUrl(path?: string) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `https://research.joyeeassets.com${path}`;
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
      <div className="font-medium text-foreground">{title}</div>
      <div className="mt-1">{description}</div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      <div>{message}</div>
      {onRetry ? (
        <Button className="mt-3" size="sm" variant="outline" onClick={onRetry}>
          <RefreshCw className="mr-2 h-4 w-4" />
          重试
        </Button>
      ) : null}
    </div>
  );
}

function ReportRow({ item, digestId }: { item: ReportCardItem; digestId?: number | string | null }) {
  const href = `/research/reports/${encodeURIComponent(item.id)}${digestId ? `?digest_id=${encodeURIComponent(String(digestId))}` : ""}`;

  return (
    <div className="rounded-md border p-4 transition-colors hover:bg-muted/40">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {item.broker ? <Badge variant="secondary">{item.broker}</Badge> : null}
            {item.report_date ? <span className="text-xs text-muted-foreground">{formatDate(item.report_date)}</span> : null}
            {item.ingest_status ? <Badge variant="outline">{item.ingest_status}</Badge> : null}
            {item.has_pdf ? <Badge variant="outline">PDF</Badge> : null}
          </div>
          <Link href={href} className="block text-base font-semibold leading-snug hover:underline">
            {reportTitle(item)}
          </Link>
          <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
            {item.formal_overview || item.brief || item.summary || item.reason || "暂无摘要"}
          </p>
          <div className="flex flex-wrap gap-2">
            {(item.tags || []).slice(0, 5).map((tag) => (
              <span key={tag} className="rounded bg-muted px-2 py-1 text-xs text-muted-foreground">
                {tag}
              </span>
            ))}
          </div>
        </div>
        <Button asChild size="sm" variant="outline" className="shrink-0">
          <Link href={href}>查看详情</Link>
        </Button>
      </div>
    </div>
  );
}

function AuthBridge({ onSaved }: { onSaved: () => void }) {
  const [token, setToken] = useState("");

  useEffect(() => {
    setToken(localStorage.getItem("research_access_token") || "");
  }, []);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">研报账号授权</CardTitle>
        <CardDescription>
          小程序的会员、积分、个人偏好、日刊历史等接口需要研报服务 token。Web 版会把这里保存的 token 透传给 research API。
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 md:flex-row">
        <Input
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="粘贴 research_access_token"
          type="password"
        />
        <Button
          onClick={() => {
            setResearchToken(token);
            onSaved();
          }}
          className="shrink-0"
        >
          保存授权
        </Button>
      </CardContent>
    </Card>
  );
}

function ReportsPanel({ data, loading, error, onReload }: { data: RecommendationResponse | null; loading: boolean; error: string; onReload: () => void }) {
  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">推荐研报</h2>
          <p className="text-sm text-muted-foreground">对应小程序首页推荐研报，匿名优先展示公共推荐内容。</p>
        </div>
        <Button size="sm" variant="outline" onClick={onReload} disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          刷新
        </Button>
      </div>
      {error ? <ErrorState message={error} onRetry={onReload} /> : null}
      {loading && !data ? <EmptyState title="正在加载推荐研报" description="从 research API 获取最新公共推荐。" /> : null}
      <div className="space-y-3">
        {(data?.items || []).map((item) => (
          <ReportRow key={item.id} item={item} />
        ))}
      </div>
      {data && !data.items.length ? <EmptyState title="暂无推荐" description="当前没有可展示的推荐研报。" /> : null}
    </section>
  );
}

function DigestsPanel({ feed, notifications, error, onReload }: { feed: DigestDetail | null; notifications: NotificationResponse | null; error: string; onReload: () => void }) {
  const digestItems = notifications?.items || [];

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">日刊 / 周刊</h2>
          <p className="text-sm text-muted-foreground">对应小程序日刊详情和往期期刊，已授权后展示个性化 feed 与历史通知。</p>
        </div>
        <Button size="sm" variant="outline" onClick={onReload}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {feed ? (
        <div className="rounded-md border p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{feed.mode || "digest"}</Badge>
            <span className="text-xs text-muted-foreground">{formatDateTime(feed.created_at)}</span>
          </div>
          <h3 className="mt-3 text-lg font-semibold">{feed.title || "当前期刊"}</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{feed.summary || feed.fallback_message || "暂无期刊摘要"}</p>
          <div className="mt-4 flex gap-2">
            <Button asChild size="sm">
              <Link href={`/research/digests/${feed.id}`}>查看期刊</Link>
            </Button>
          </div>
        </div>
      ) : null}
      <div className="space-y-3">
        {digestItems.map((item) => (
          <div key={item.id} className="rounded-md border p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={item.is_read ? "outline" : "secondary"}>{item.is_read ? "已读" : "未读"}</Badge>
                  <span className="text-xs text-muted-foreground">{formatDateTime(item.created_at)}</span>
                  {item.payload?.mode ? <span className="text-xs text-muted-foreground">{item.payload.mode}</span> : null}
                </div>
                <h3 className="mt-2 font-semibold">{item.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{item.body}</p>
              </div>
              <Button asChild size="sm" variant="outline">
                <Link href={`/research/digests/${item.id}`}>打开</Link>
              </Button>
            </div>
          </div>
        ))}
      </div>
      {!feed && !digestItems.length ? (
        <EmptyState title="需要研报账号授权" description="保存研报 token 后，可查看当前日刊/周刊和往期期刊历史。" />
      ) : null}
    </section>
  );
}

function FundsPanel({ archive, holdings, activeFundId, error, onSelectFund }: {
  archive: HedgeFundArchiveResponse | null;
  holdings: HedgeFundHoldingsResponse | null;
  activeFundId: string;
  error: string;
  onSelectFund: (fund: HedgeFundArchiveFund) => void;
}) {
  const [query, setQuery] = useState("");
  const funds = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const raw = archive?.funds || [];
    if (!normalized) return raw;
    return raw.filter((fund) => `${fund.name} ${fund.name_zh || ""} ${fund.founder_name} ${fund.core_strategy}`.toLowerCase().includes(normalized));
  }, [archive, query]);

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">机构图鉴</h2>
        <p className="text-sm text-muted-foreground">对应小程序机构图鉴，展示对冲基金档案、策略、创始人与 13F 持仓。</p>
      </div>
      {error ? <ErrorState message={error} /> : null}
      <div className="flex items-center gap-2 rounded-md border px-3">
        <Search className="h-4 w-4 text-muted-foreground" />
        <Input className="border-0 focus-visible:ring-0" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索机构、创始人、策略" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="grid gap-3 md:grid-cols-2">
          {funds.slice(0, 24).map((fund) => (
            <button
              key={fund.id}
              type="button"
              onClick={() => onSelectFund(fund)}
              className={`rounded-md border p-4 text-left transition-colors hover:bg-muted/40 ${activeFundId === fund.id ? "border-primary" : ""}`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="font-semibold">{fund.name_zh || fund.name}</div>
                <Badge variant="outline">{fund.logo_text}</Badge>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">{fund.name}</div>
              <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">{fund.latest_dynamic || fund.signature}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {fund.strategy_names.slice(0, 3).map((strategy) => (
                  <span key={strategy} className="rounded bg-muted px-2 py-1 text-xs text-muted-foreground">
                    {strategy}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
        <div className="rounded-md border p-4">
          <h3 className="font-semibold">持仓概览</h3>
          {holdings ? (
            <div className="mt-3 space-y-3">
              <div className="text-sm text-muted-foreground">
                {holdings.fund.name} · {holdings.selected_period || holdings.periods?.[0]?.report_period || "最新披露"}
              </div>
              {holdings.holdings.slice(0, 10).map((holding) => (
                <div key={`${holding.security_name}-${holding.ticker || ""}`} className="flex items-start justify-between gap-3 border-t pt-3 text-sm">
                  <div>
                    <div className="font-medium">{holding.security_name}</div>
                    <div className="text-xs text-muted-foreground">{holding.ticker || "-"} · {holding.source_name || "13F"}</div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div>{formatNumber(holding.market_value_usd)} USD</div>
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
    </section>
  );
}

function MallPanel({ mall, error, onReload }: { mall: PointsMallResponse | null; error: string; onReload: () => void }) {
  const [wishOpen, setWishOpen] = useState(false);
  const [redeemItem, setRedeemItem] = useState<PointsMallItem | null>(null);
  const [wishBook, setWishBook] = useState("");
  const [wishNote, setWishNote] = useState("");
  const [wishStatus, setWishStatus] = useState("");
  const [redeemForm, setRedeemForm] = useState({ recipient_name: "", recipient_phone: "", shipping_address: "" });
  const [submitting, setSubmitting] = useState(false);
  const items = mall?.items?.length ? mall.items : FALLBACK_MALL_ITEMS;

  async function submitWish() {
    const normalizedBook = wishBook.trim().replace(/\s+/g, " ");
    const normalizedNote = wishNote.trim().replace(/\s+/g, " ");
    if (normalizedBook.length < 2) {
      setWishStatus("请填写想兑换的书");
      return;
    }
    setSubmitting(true);
    setWishStatus("");
    try {
      await submitFeedback({
        category: "points_mall_wish",
        content: `积分商城许愿：${normalizedBook}${normalizedNote ? `；补充：${normalizedNote}` : ""}`,
        page_path: "/research?tab=mall",
        metadata: {
          wished_book: normalizedBook,
          note: normalizedNote,
        },
      });
      setWishBook("");
      setWishNote("");
      setWishStatus("已收到许愿，可在 research 后台反馈列表看到。");
    } catch (error) {
      setWishStatus(error instanceof Error ? error.message : "许愿提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitRedeem() {
    if (!redeemItem) return;
    setSubmitting(true);
    try {
      await redeemPointsMallItem({
        item_code: redeemItem.code,
        ...redeemForm,
      });
      setRedeemItem(null);
      setRedeemForm({ recipient_name: "", recipient_phone: "", shipping_address: "" });
      onReload();
    } catch (error) {
      alert(error instanceof Error ? error.message : "兑换失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">积分商城</h2>
          <p className="text-sm text-muted-foreground">对应小程序积分商城，书籍信息和许愿入口同步到研报反馈后台。</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setWishOpen(true)}>
            <Heart className="mr-2 h-4 w-4" />
            许愿
          </Button>
          <Button size="sm" variant="outline" onClick={onReload}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
        </div>
      </div>
      {error ? <ErrorState message={`${error}。未授权时先展示当前小程序同款书籍，兑换需研报账号授权。`} /> : null}
      <div className="grid gap-4 md:grid-cols-3">
        {items.map((item) => (
          <div key={item.code} className="rounded-md border p-4">
            <div className="aspect-[3/4] overflow-hidden rounded-md border bg-muted">
              {item.cover_image ? (
                <img src={imageUrl(item.cover_image)} alt={item.name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center text-3xl font-bold text-muted-foreground">{item.name.slice(1, 2)}</div>
              )}
            </div>
            <h3 className="mt-4 font-semibold">{item.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{item.subtitle}</p>
            <p className="mt-3 min-h-12 text-sm leading-6 text-muted-foreground">{item.description}</p>
            <div className="mt-4 flex items-center justify-between">
              <div>
                <div className="text-lg font-bold">{formatNumber(item.points_cost)} 分</div>
                <div className="text-xs text-muted-foreground">库存 {item.stock}</div>
              </div>
              <Button size="sm" disabled={!item.can_redeem || item.stock <= 0} onClick={() => setRedeemItem(item)}>
                兑换
              </Button>
            </div>
          </div>
        ))}
      </div>
      {mall?.redemptions?.length ? (
        <div className="rounded-md border p-4">
          <h3 className="font-semibold">兑换记录</h3>
          <div className="mt-3 space-y-2">
            {mall.redemptions.map((item) => (
              <div key={item.id} className="flex items-center justify-between border-t pt-2 text-sm">
                <span>{item.item_name}</span>
                <span className="text-muted-foreground">{item.status} · {formatDateTime(item.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <Dialog open={wishOpen} onOpenChange={setWishOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>许愿想兑换的书</DialogTitle>
            <DialogDescription>提交后会进入 research 后台「积分商城许愿」反馈列表。</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>书名 / 作者 / 版本</Label>
              <Input value={wishBook} onChange={(event) => setWishBook(event.target.value)} placeholder="例如：某本中译版书籍" />
            </div>
            <div className="space-y-2">
              <Label>补充说明</Label>
              <Textarea value={wishNote} onChange={(event) => setWishNote(event.target.value)} placeholder="可选：出版社、译者、为什么想兑换" />
            </div>
            {wishStatus ? <div className="text-sm text-muted-foreground">{wishStatus}</div> : null}
          </div>
          <DialogFooter>
            <Button onClick={submitWish} disabled={submitting}>
              {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
              提交许愿
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!redeemItem} onOpenChange={(open) => !open && setRedeemItem(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>兑换 {redeemItem?.name}</DialogTitle>
            <DialogDescription>兑换会消耗积分并生成发货记录。</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Input value={redeemForm.recipient_name} onChange={(event) => setRedeemForm((prev) => ({ ...prev, recipient_name: event.target.value }))} placeholder="收件人" />
            <Input value={redeemForm.recipient_phone} onChange={(event) => setRedeemForm((prev) => ({ ...prev, recipient_phone: event.target.value }))} placeholder="联系电话" />
            <Textarea value={redeemForm.shipping_address} onChange={(event) => setRedeemForm((prev) => ({ ...prev, shipping_address: event.target.value }))} placeholder="收货地址" />
          </div>
          <DialogFooter>
            <Button onClick={submitRedeem} disabled={submitting}>
              确认兑换
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function MembershipPanel({ overview, profile, error, onCheckIn, onReload }: {
  overview: BillingOverview | null;
  profile: UserProfileResponse | null;
  error: string;
  onCheckIn: () => void;
  onReload: () => void;
}) {
  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">权益中心 / 我的</h2>
          <p className="text-sm text-muted-foreground">对应小程序权益中心、我的页面、签到、邀请和订单概览。</p>
        </div>
        <Button size="sm" variant="outline" onClick={onReload}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {overview || profile ? (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-md border p-4">
            <div className="text-sm text-muted-foreground">用户</div>
            <div className="mt-2 text-xl font-semibold">{profile?.nickname || "研报用户"}</div>
            <div className="mt-1 text-sm text-muted-foreground">ID #{profile?.user_id || "-"}</div>
          </div>
          <div className="rounded-md border p-4">
            <div className="text-sm text-muted-foreground">会员</div>
            <div className="mt-2 text-xl font-semibold">{overview?.active_membership?.is_active ? "已开通" : "未开通"}</div>
            <div className="mt-1 text-sm text-muted-foreground">到期 {formatDate(overview?.active_membership?.expires_at)}</div>
          </div>
          <div className="rounded-md border p-4">
            <div className="text-sm text-muted-foreground">积分</div>
            <div className="mt-2 text-xl font-semibold">{formatNumber(overview?.points_mall?.points?.remaining || 0)}</div>
            <Button className="mt-3" size="sm" onClick={onCheckIn} disabled={overview?.daily_checkin?.checked_in_today}>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              {overview?.daily_checkin?.checked_in_today ? "今日已签到" : `签到 +${overview?.daily_checkin?.reward_points || 0}`}
            </Button>
          </div>
        </div>
      ) : (
        <EmptyState title="需要研报账号授权" description="保存研报 token 后，可查看会员、积分、邀请、签到和订单。" />
      )}
      {overview?.recent_orders?.length ? (
        <div className="rounded-md border p-4">
          <h3 className="font-semibold">近期订单</h3>
          <div className="mt-3 space-y-2">
            {overview.recent_orders.map((order) => (
              <div key={order.id} className="flex items-center justify-between border-t pt-2 text-sm">
                <span>{order.title}</span>
                <span className="text-muted-foreground">{formatMoneyFen(order.amount_fen)} · {order.payment_status}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function PreferencesPanel({ profile, error, onReload }: { profile: UserProfileResponse | null; error: string; onReload: () => void }) {
  const [industries, setIndustries] = useState("");
  const [themes, setThemes] = useState("");
  const [keywords, setKeywords] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (!profile) return;
    setIndustries(profile.preferences.industries.join("、"));
    setThemes(profile.preferences.themes.join("、"));
    setKeywords(profile.preferences.custom_keywords.join("、"));
    setCustomPrompt(profile.preferences.custom_prompt || "");
  }, [profile]);

  function splitTags(value: string) {
    return [...new Set(value.split(/[,\n，、；;\s]/).map((item) => item.trim()).filter(Boolean))];
  }

  async function save() {
    if (!profile) return;
    setStatus("");
    try {
      await updateUserPreferences({
        ...profile.preferences,
        industries: splitTags(industries),
        themes: splitTags(themes),
        custom_keywords: splitTags(keywords),
        custom_prompt: customPrompt.trim(),
      });
      setStatus("偏好已保存");
      onReload();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存失败");
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">兴趣设置 / 资料设置</h2>
        <p className="text-sm text-muted-foreground">对应小程序兴趣设置和资料设置，支持行业、主题、关键词、自定义提示词。</p>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {profile ? (
        <div className="space-y-4 rounded-md border p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>行业</Label>
              <Textarea value={industries} onChange={(event) => setIndustries(event.target.value)} placeholder="消费、科技、医药" />
            </div>
            <div className="space-y-2">
              <Label>主题</Label>
              <Textarea value={themes} onChange={(event) => setThemes(event.target.value)} placeholder="AI、出海、周期" />
            </div>
          </div>
          <div className="space-y-2">
            <Label>自定义关键词</Label>
            <Input value={keywords} onChange={(event) => setKeywords(event.target.value)} placeholder="用逗号或空格分隔" />
          </div>
          <div className="space-y-2">
            <Label>自定义推荐要求</Label>
            <Textarea value={customPrompt} onChange={(event) => setCustomPrompt(event.target.value)} placeholder="例如：更关注商业模式和估值变化" />
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={save}>保存偏好</Button>
            {status ? <span className="text-sm text-muted-foreground">{status}</span> : null}
          </div>
        </div>
      ) : (
        <EmptyState title="需要研报账号授权" description="保存研报 token 后，可编辑个性化推荐偏好。" />
      )}
    </section>
  );
}

function FeedbackPanel() {
  const [category, setCategory] = useState("feature");
  const [content, setContent] = useState("");
  const [contact, setContact] = useState("");
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    const normalized = content.trim().replace(/\s+/g, " ");
    if (normalized.length < 4) {
      setStatus("请补充更具体的反馈内容");
      return;
    }
    setSubmitting(true);
    setStatus("");
    try {
      const result = await submitFeedback({
        category,
        content: normalized,
        contact,
        page_path: "/research?tab=feedback",
      });
      setContent("");
      setStatus(`已收到反馈 #${result.id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">意见反馈</h2>
        <p className="text-sm text-muted-foreground">对应小程序意见反馈，提交后进入 research 后台反馈管理。</p>
      </div>
      <div className="space-y-4 rounded-md border p-4">
        <div className="space-y-2">
          <Label>反馈类型</Label>
          <select className="w-full rounded-md border bg-background px-3 py-2 text-sm" value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="recommendation">内容推荐不准</option>
            <option value="report_access">研报打不开</option>
            <option value="summary_audio">音频/摘要问题</option>
            <option value="feature">功能建议</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label>反馈内容</Label>
          <Textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="请描述问题、期待的功能或上下文" />
        </div>
        <div className="space-y-2">
          <Label>联系方式</Label>
          <Input value={contact} onChange={(event) => setContact(event.target.value)} placeholder="可选" />
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={submit} disabled={submitting}>
            {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
            提交反馈
          </Button>
          {status ? <span className="text-sm text-muted-foreground">{status}</span> : null}
        </div>
      </div>
    </section>
  );
}

export function ResearchHub() {
  const [activeTab, setActiveTab] = useState<TabValue>("reports");
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [homeFeed, setHomeFeed] = useState<DigestDetail | null>(null);
  const [notifications, setNotifications] = useState<NotificationResponse | null>(null);
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [billing, setBilling] = useState<BillingOverview | null>(null);
  const [mall, setMall] = useState<PointsMallResponse | null>(null);
  const [archive, setArchive] = useState<HedgeFundArchiveResponse | null>(null);
  const [activeFundId, setActiveFundId] = useState("");
  const [holdings, setHoldings] = useState<HedgeFundHoldingsResponse | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);

  async function loadPublic() {
    setLoadingRecommendations(true);
    try {
      const [nextRecommendations, nextArchive] = await Promise.all([
        getPublicRecommendations(12),
        getHedgeFundArchive(),
      ]);
      setRecommendations(nextRecommendations);
      setArchive(nextArchive);
      setErrors((prev) => ({ ...prev, reports: "", funds: "" }));
      const firstFund = nextArchive.funds[0];
      if (firstFund) {
        setActiveFundId(firstFund.id);
        getHedgeFundHoldings(firstFund.id).then(setHoldings).catch(() => setHoldings(null));
      }
    } catch (error) {
      setErrors((prev) => ({ ...prev, reports: error instanceof Error ? error.message : "公共内容加载失败" }));
    } finally {
      setLoadingRecommendations(false);
    }
  }

  async function loadPrivate() {
    const nextErrors: Record<string, string> = {};
    try {
      const [feed, notice, user, overview, pointsMall] = await Promise.all([
        getHomeFeed().catch((error) => {
          nextErrors.digests = error instanceof Error ? error.message : "期刊加载失败";
          return null;
        }),
        getNotifications(20).catch(() => null),
        getUserProfile().catch((error) => {
          nextErrors.profile = error instanceof Error ? error.message : "资料加载失败";
          return null;
        }),
        getBillingOverview().catch((error) => {
          nextErrors.membership = error instanceof Error ? error.message : "权益加载失败";
          return null;
        }),
        getPointsMall().catch((error) => {
          nextErrors.mall = error instanceof Error ? error.message : "积分商城加载失败";
          return null;
        }),
      ]);
      setHomeFeed(feed);
      setNotifications(notice);
      setProfile(user);
      setBilling(overview);
      setMall(pointsMall);
    } finally {
      setErrors((prev) => ({ ...prev, ...nextErrors }));
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get("tab") as TabValue | null;
    if (tab && MODULES.some((item) => item.value === tab)) {
      setActiveTab(tab);
    }
    loadPublic();
    loadPrivate();
  }, []);

  function refreshAll() {
    loadPublic();
    loadPrivate();
  }

  async function selectFund(fund: HedgeFundArchiveFund) {
    setActiveFundId(fund.id);
    setHoldings(null);
    try {
      setHoldings(await getHedgeFundHoldings(fund.id));
      setErrors((prev) => ({ ...prev, funds: "" }));
    } catch (error) {
      setErrors((prev) => ({ ...prev, funds: error instanceof Error ? error.message : "持仓加载失败" }));
    }
  }

  async function checkIn() {
    try {
      await dailyCheckIn();
      const overview = await getBillingOverview();
      setBilling(overview);
    } catch (error) {
      setErrors((prev) => ({ ...prev, membership: error instanceof Error ? error.message : "签到失败" }));
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">Research Web</Badge>
              <Badge variant="secondary">小程序功能迁移</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-bold">研报中心</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              将研报小程序的首页、期刊、研报详情、机构图鉴、积分商城、权益、偏好和反馈功能整合到 KeelTrader Web。
            </p>
          </div>
          <Button variant="outline" onClick={refreshAll}>
            <RefreshCw className="mr-2 h-4 w-4" />
            全部刷新
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-7">
          {MODULES.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.value}
                type="button"
                onClick={() => setActiveTab(item.value)}
                className={`rounded-md border p-3 text-left transition-colors hover:bg-muted/40 ${activeTab === item.value ? "border-primary bg-muted/50" : ""}`}
              >
                <Icon className="h-5 w-5" />
                <div className="mt-2 text-sm font-medium">{item.label}</div>
              </button>
            );
          })}
        </div>

        <AuthBridge onSaved={refreshAll} />

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as TabValue)} className="space-y-5">
          <TabsList className="h-auto flex-wrap justify-start">
            {MODULES.map((item) => (
              <TabsTrigger key={item.value} value={item.value}>
                {item.label}
              </TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="reports">
            <ReportsPanel data={recommendations} loading={loadingRecommendations} error={errors.reports || ""} onReload={loadPublic} />
          </TabsContent>
          <TabsContent value="digests">
            <DigestsPanel feed={homeFeed} notifications={notifications} error={errors.digests || ""} onReload={loadPrivate} />
          </TabsContent>
          <TabsContent value="funds">
            <FundsPanel archive={archive} holdings={holdings} activeFundId={activeFundId} error={errors.funds || ""} onSelectFund={selectFund} />
          </TabsContent>
          <TabsContent value="mall">
            <MallPanel mall={mall} error={errors.mall || ""} onReload={loadPrivate} />
          </TabsContent>
          <TabsContent value="membership">
            <MembershipPanel overview={billing} profile={profile} error={errors.membership || errors.profile || ""} onCheckIn={checkIn} onReload={loadPrivate} />
          </TabsContent>
          <TabsContent value="preferences">
            <PreferencesPanel profile={profile} error={errors.profile || ""} onReload={loadPrivate} />
          </TabsContent>
          <TabsContent value="feedback">
            <FeedbackPanel />
          </TabsContent>
        </Tabs>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-md border p-4">
            <Sparkles className="h-5 w-5" />
            <div className="mt-2 font-medium">公共推荐可匿名访问</div>
            <div className="mt-1 text-sm text-muted-foreground">未授权用户也能阅读公共研报推荐和机构图鉴。</div>
          </div>
          <div className="rounded-md border p-4">
            <Bell className="h-5 w-5" />
            <div className="mt-2 font-medium">个性化功能使用真实接口</div>
            <div className="mt-1 text-sm text-muted-foreground">会员、积分、偏好、历史期刊使用 research API token。</div>
          </div>
          <div className="rounded-md border p-4">
            <Star className="h-5 w-5" />
            <div className="mt-2 font-medium">反馈进入同一后台</div>
            <div className="mt-1 text-sm text-muted-foreground">意见反馈和积分商城许愿都会出现在 research admin。</div>
          </div>
        </div>
      </div>
    </div>
  );
}
