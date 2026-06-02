"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Bell,
  BookOpen,
  Building2,
  CheckCircle2,
  CreditCard,
  Download,
  Gift,
  Heart,
  History,
  Loader2,
  Mic,
  MessageSquare,
  RefreshCw,
  Search,
  Send,
  Settings2,
  Sparkles,
  Star,
  Ticket,
  Upload,
  X,
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
  addUserPreferenceTag,
  createBillingOrder,
  downloadHedgeFundMiniappCode,
  getBillingOverview,
  getBillingCatalog,
  getHedgeFundArchive,
  getHedgeFundHoldings,
  getHomeFeed,
  getInviteOverview,
  getNotifications,
  getOfficialBindingStatus,
  getPointsMall,
  getRecommendations,
  getReportFreshness,
  getUserProfile,
  markAllNotificationsRead,
  markNotificationRead,
  prepareBillingOrderPayment,
  redeemPointsMallItem,
  refreshNotifications,
  removeUserPreferenceTag,
  setResearchToken,
  submitFeedback,
  trackClientEvent,
  transcribePreferenceAudio,
  updateAccountProfile,
  updateMiniappDeliveryProfile,
  updateOnboardingProfile,
  updateUserPreferences,
  uploadAvatar,
  type BillingOverview,
  type OfficialBindingStatus,
  type DigestDetail,
  type HedgeFundArchiveFund,
  type HedgeFundArchiveResponse,
  type HedgeFundHoldingsResponse,
  type NotificationResponse,
  type PointsMallItem,
  type PointsMallResponse,
  type ProductItem,
  type InviteOverview,
  type RecommendationResponse,
  type ReportFreshness,
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

const BLOCKED_KEYWORDS = ["test", "testing", "asdf", "qwer", "null", "none", "unknown", "测试", "无", "不知道", "随便"];

const PROMPT_TEMPLATES = [
  {
    id: "concise",
    title: "更简洁",
    description: "摘要更短，直接说重点，少空话。",
    prompt: "请用更简洁的中文写摘要，直接说重点，少空话，不要重复标题。",
  },
  {
    id: "plain",
    title: "更通俗",
    description: "像解释给非专业用户，少术语。",
    prompt: "请用更通俗的中文写摘要，像解释给非专业用户一样，少用术语，表达清楚。",
  },
  {
    id: "structured",
    title: "更结构化",
    description: "先结论，再重点，再补充说明。",
    prompt: "请把摘要写得更结构化：先说结论，再列重点，最后补充说明，层次清楚。",
  },
  {
    id: "insight",
    title: "更关注启发",
    description: "更强调对行业、品牌、经营动作的实际启发。",
    prompt: "请更关注这篇内容对行业、品牌和经营动作的实际启发，少写空泛判断，多写具体意义。",
  },
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

function ReportsPanel({
  data,
  freshness,
  mode,
  loading,
  error,
  onReload,
  onModeChange,
}: {
  data: RecommendationResponse | null;
  freshness: ReportFreshness | null;
  mode: "public" | "personalized";
  loading: boolean;
  error: string;
  onReload: () => void;
  onModeChange: (mode: "public" | "personalized") => void;
}) {
  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">推荐研报</h2>
          <p className="text-sm text-muted-foreground">对应小程序首页推荐研报，可切换公共推荐和授权后的个性化推荐。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant={mode === "public" ? "secondary" : "outline"} onClick={() => onModeChange("public")}>
            公共推荐
          </Button>
          <Button size="sm" variant={mode === "personalized" ? "secondary" : "outline"} onClick={() => onModeChange("personalized")}>
            个性化
          </Button>
          <Button size="sm" variant="outline" onClick={onReload} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
        </div>
      </div>
      {freshness ? (
        <div className="grid gap-3 md:grid-cols-4">
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">最新研报日</div>
            <div className="mt-1 font-semibold">{freshness.latest_report_date || "-"}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">今日研报</div>
            <div className="mt-1 font-semibold">{formatNumber(freshness.today_report_count)}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">本周研报</div>
            <div className="mt-1 font-semibold">{formatNumber(freshness.current_week_report_count)}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">OCR 待处理</div>
            <div className="mt-1 font-semibold">{formatNumber(freshness.ocr_backlog_count)}</div>
          </div>
        </div>
      ) : null}
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

function DigestsPanel({
  feed,
  notifications,
  error,
  onReload,
  onRefreshNotifications,
  onMarkRead,
  onMarkAllRead,
}: {
  feed: DigestDetail | null;
  notifications: NotificationResponse | null;
  error: string;
  onReload: () => void;
  onRefreshNotifications: () => void;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
}) {
  const digestItems = notifications?.items || [];

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">日刊 / 周刊</h2>
          <p className="text-sm text-muted-foreground">对应小程序日刊详情和往期期刊，已授权后展示个性化 feed 与历史通知。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={onRefreshNotifications}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新通知
          </Button>
          <Button size="sm" variant="outline" onClick={onMarkAllRead} disabled={!digestItems.length}>
            <CheckCircle2 className="mr-2 h-4 w-4" />
            全部已读
          </Button>
          <Button size="sm" variant="outline" onClick={onReload}>
            重新加载
          </Button>
        </div>
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
              <div className="flex shrink-0 gap-2">
                {!item.is_read ? (
                  <Button size="sm" variant="outline" onClick={() => onMarkRead(item.id)}>
                    标为已读
                  </Button>
                ) : null}
                <Button asChild size="sm" variant="outline">
                  <Link href={`/research/digests/${item.id}`}>打开</Link>
                </Button>
              </div>
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

function FundsPanel({ archive, holdings, activeFundId, activeMarket, error, onSelectFund, onSelectMarket, onDownloadMiniappCode }: {
  archive: HedgeFundArchiveResponse | null;
  holdings: HedgeFundHoldingsResponse | null;
  activeFundId: string;
  activeMarket: string;
  error: string;
  onSelectFund: (fund: HedgeFundArchiveFund) => void;
  onSelectMarket: (market: string) => void;
  onDownloadMiniappCode: (fundId: string) => void;
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
                <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
                  可用披露期：{holdings.periods.slice(0, 6).map((period) => `${period.report_period}(${period.holding_count})`).join(" / ")}
                </div>
              ) : null}
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

function MembershipPanel({ overview, profile, invite, catalog, officialBinding, error, onCheckIn, onReload, onCreateOrder }: {
  overview: BillingOverview | null;
  profile: UserProfileResponse | null;
  invite: InviteOverview | null;
  catalog: ProductItem[];
  officialBinding: OfficialBindingStatus | null;
  error: string;
  onCheckIn: () => void;
  onReload: () => void;
  onCreateOrder: (product: ProductItem) => void;
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
          <div className="rounded-md border p-4 md:col-span-3">
            <div className="text-sm text-muted-foreground">公众号绑定</div>
            <div className="mt-2 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="font-semibold">{officialBinding?.bound ? "已绑定" : "未绑定"}</div>
                <div className="text-sm text-muted-foreground">
                  {officialBinding?.binding
                    ? `${officialBinding.binding.official_openid_masked} · ${officialBinding.binding.subscribe_status}`
                    : "对应小程序公众号绑定状态，用于接收推送。"}
                </div>
              </div>
              <Badge variant={officialBinding?.bound ? "secondary" : "outline"}>
                {officialBinding?.binding?.status || "unbound"}
              </Badge>
            </div>
          </div>
        </div>
      ) : (
        <EmptyState title="需要研报账号授权" description="保存研报 token 后，可查看会员、积分、邀请、签到和订单。" />
      )}
      {catalog.length ? (
        <div className="rounded-md border p-4">
          <h3 className="font-semibold">会员商品</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            {catalog.map((product) => (
              <div key={product.code} className="rounded-md border p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium">{product.name}</div>
                  <Badge variant={product.is_active ? "secondary" : "outline"}>{product.product_type}</Badge>
                </div>
                <div className="mt-2 text-2xl font-bold">{formatMoneyFen(product.price_fen)}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  原价 {formatMoneyFen(product.original_price_fen)} · {product.duration_days ? `${product.duration_days} 天` : "权益商品"}
                </div>
                <Button className="mt-4 w-full" size="sm" disabled={!product.is_active} onClick={() => onCreateOrder(product)}>
                  <CreditCard className="mr-2 h-4 w-4" />
                  创建订单
                </Button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {invite ? (
        <div className="rounded-md border p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="font-semibold">邀请奖励</h3>
              <p className="mt-1 text-sm text-muted-foreground">{invite.summary.reward_copy || invite.summary.reward_rule?.display_text || "邀请好友可获得奖励。"}</p>
            </div>
            <Badge variant="secondary">邀请码 {invite.invite_code}</Badge>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-md bg-muted/50 p-3">
              <div className="text-xs text-muted-foreground">已邀请</div>
              <div className="mt-1 font-semibold">{formatNumber(invite.summary.invited_count)}</div>
            </div>
            <div className="rounded-md bg-muted/50 p-3">
              <div className="text-xs text-muted-foreground">已奖励</div>
              <div className="mt-1 font-semibold">{formatNumber(invite.summary.rewarded_count)}</div>
            </div>
            <div className="rounded-md bg-muted/50 p-3">
              <div className="text-xs text-muted-foreground">剩余邀请积分</div>
              <div className="mt-1 font-semibold">{formatNumber(invite.summary.invite_points?.remaining || 0)}</div>
            </div>
          </div>
          {invite.records.length ? (
            <div className="mt-4 space-y-2">
              {invite.records.slice(0, 6).map((record) => (
                <div key={record.id} className="flex items-center justify-between border-t pt-2 text-sm">
                  <span>{record.invited_nickname || "匿名用户"}</span>
                  <span className="text-muted-foreground">{record.status} · {formatDateTime(record.created_at)}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
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
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);
  const [nickname, setNickname] = useState("");
  const [industries, setIndustries] = useState("");
  const [occupation, setOccupation] = useState("");
  const [themes, setThemes] = useState("");
  const [updateFrequency, setUpdateFrequency] = useState("每周");
  const [languagePreference, setLanguagePreference] = useState("");
  const [keywords, setKeywords] = useState("");
  const [keywordDraft, setKeywordDraft] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [deliveryEnabled, setDeliveryEnabled] = useState(false);
  const [subscriptionStatus, setSubscriptionStatus] = useState("unknown");
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (!profile) return;
    setNickname(profile.nickname || "");
    setIndustries((profile.onboarding_profile?.industries?.length ? profile.onboarding_profile.industries : profile.preferences.industries).join("、"));
    setOccupation(profile.onboarding_profile?.occupation || "");
    setThemes(profile.preferences.themes.join("、"));
    setUpdateFrequency(profile.preferences.update_frequency || "每周");
    setLanguagePreference(profile.preferences.language_preference || "");
    setKeywords(profile.preferences.custom_keywords.join("、"));
    setCustomPrompt(profile.preferences.custom_prompt || "");
    setDeliveryEnabled(profile.delivery.enabled);
    setSubscriptionStatus(profile.delivery.subscription_status || "unknown");
  }, [profile]);

  function splitTags(value: string) {
    return [...new Set(value.split(/[,\n，、；;\s]/).map((item) => item.trim()).filter(Boolean))];
  }

  function parseKeywordInput(rawText: string) {
    return rawText
      .replace(/[。；;、]/g, "，")
      .replace(/\s+/g, "，")
      .split(/[,\n，]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function hasRepeatedNoise(value: string) {
    const compact = value.replace(/\s+/g, "").toLowerCase();
    return compact.length >= 6 && new Set(compact.split("")).size === 1;
  }

  function validateCustomKeyword(value: string) {
    const normalized = value.trim().replace(/\s+/g, " ");
    if (normalized.length < 2) return { value: normalized, error: "自定义关注点至少 2 个字" };
    if (normalized.length > 20) return { value: normalized, error: "自定义关注点最多 20 个字" };
    if (BLOCKED_KEYWORDS.includes(normalized.toLowerCase())) return { value: normalized, error: "请填写真实关注点" };
    if (/^\d+$/.test(normalized) || !/[\w\u4e00-\u9fff]/.test(normalized)) return { value: normalized, error: "自定义关注点请填写文字内容" };
    if (/https?:\/\/|www\.|[\w.+-]+@[\w-]+(?:\.[\w-]+)+|(?:\+?\d[\d\s-]{6,}\d)/i.test(normalized)) {
      return { value: normalized, error: "自定义关注点不能包含链接或联系方式" };
    }
    if (hasRepeatedNoise(normalized)) return { value: normalized, error: "请填写真实关注点" };
    return { value: normalized, error: "" };
  }

  function normalizeCustomKeywords(rawItems: string[]) {
    const normalized: string[] = [];
    for (const item of rawItems) {
      const result = validateCustomKeyword(item);
      if (result.error) return { values: normalized, error: result.error };
      if (!normalized.includes(result.value)) normalized.push(result.value);
      if (normalized.length > 10) return { values: normalized.slice(0, 10), error: "自定义关注点最多 10 个" };
    }
    return { values: normalized, error: "" };
  }

  function joinTags(values: string[]) {
    return [...new Set(values.map((item) => item.trim()).filter(Boolean))].join("、");
  }

  function patchTagField(type: "industry" | "theme" | "custom_keyword", value: string, action: "add" | "remove") {
    const mutate = (raw: string) => {
      const current = splitTags(raw);
      const next = action === "add" ? [...current, value] : current.filter((item) => item !== value);
      return joinTags(next);
    };
    if (type === "industry") setIndustries(mutate);
    if (type === "theme") setThemes(mutate);
    if (type === "custom_keyword") setKeywords(mutate);
  }

  function appendKeywords(rawText: string) {
    const parsed = parseKeywordInput(rawText);
    const normalizedAddition = normalizeCustomKeywords(parsed);
    if (normalizedAddition.error) {
      setStatus(normalizedAddition.error);
      return;
    }
    const addition = normalizedAddition.values;
    if (!addition.length) return;
    const merged = normalizeCustomKeywords([...splitTags(keywords), ...addition]);
    if (merged.error) {
      setStatus(merged.error);
      setKeywords(joinTags(merged.values));
      return;
    }
    setKeywords(joinTags(merged.values));
    setKeywordDraft("");
    setStatus(`已添加 ${addition.join("、")}`);
  }

  async function mutatePreferenceTag(type: "industry" | "theme" | "custom_keyword", value: string, action: "add" | "remove") {
    const normalized = value.trim();
    if (!normalized) return;
    setUploading(true);
    setStatus("");
    try {
      if (action === "add") {
        await addUserPreferenceTag(type, normalized);
      } else {
        await removeUserPreferenceTag(type, normalized);
      }
      patchTagField(type, normalized, action);
      setStatus(action === "add" ? `已添加 ${normalized}` : `已移除 ${normalized}`);
      onReload();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "偏好标签更新失败");
    } finally {
      setUploading(false);
    }
  }

  async function handleAvatarUpload(file?: File | null) {
    if (!file) return;
    setUploading(true);
    setStatus("");
    try {
      await uploadAvatar(file);
      setStatus("头像已上传");
      trackClientEvent({
        event_name: "web_avatar_uploaded",
        page_path: "/research?tab=preferences",
        metadata: { file_type: file.type, file_size: file.size },
      }).catch(() => undefined);
      onReload();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "头像上传失败");
    } finally {
      setUploading(false);
      if (avatarInputRef.current) avatarInputRef.current.value = "";
    }
  }

  async function handlePreferenceAudio(file?: File | null) {
    if (!file) return;
    setUploading(true);
    setStatus("");
    try {
      const result = await transcribePreferenceAudio(file);
      const nextTags = joinTags([...splitTags(keywords), ...(result.tags || [])]);
      setKeywords(nextTags);
      if (result.text) {
        setCustomPrompt((prev) => [prev.trim(), `语音偏好：${result.text}`].filter(Boolean).join("\n"));
      }
      setStatus(result.tags?.length ? `语音已识别：${result.tags.join("、")}` : "语音已识别，请检查偏好内容");
      trackClientEvent({
        event_name: "web_preference_audio_transcribed",
        page_path: "/research?tab=preferences",
        metadata: { file_type: file.type, file_size: file.size, tag_count: result.tags?.length || 0 },
      }).catch(() => undefined);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "语音识别失败");
    } finally {
      setUploading(false);
      if (audioInputRef.current) audioInputRef.current.value = "";
    }
  }

  async function save() {
    if (!profile) return;
    setSaving(true);
    setStatus("");
    try {
      const normalizedNickname = nickname.trim().replace(/\s+/g, " ");
      const normalizedIndustries = splitTags(industries).slice(0, 8);
      const normalizedOccupation = occupation.trim().replace(/\s+/g, " ");
      const normalizedKeywords = normalizeCustomKeywords(splitTags(keywords));
      if (normalizedKeywords.error) {
        setStatus(normalizedKeywords.error);
        setSaving(false);
        return;
      }
      await Promise.all([
        updateAccountProfile({ nickname: normalizedNickname || profile.nickname }),
        updateOnboardingProfile({
          industries: normalizedIndustries.slice(0, 2),
          occupation: normalizedOccupation,
        }),
        updateUserPreferences({
          ...profile.preferences,
          industries: normalizedIndustries,
          themes: splitTags(themes),
          update_frequency: updateFrequency || "每周",
          language_preference: languagePreference || null,
          custom_keywords: normalizedKeywords.values,
          custom_prompt: customPrompt.trim(),
        }),
        updateMiniappDeliveryProfile({
          enabled: deliveryEnabled,
          subscription_status: subscriptionStatus,
        }),
      ]);
      trackClientEvent({
        event_name: "web_preferences_saved",
        page_path: "/research?tab=preferences",
        status: "success",
        metadata: {
          industries_count: normalizedIndustries.length,
          themes_count: splitTags(themes).length,
          custom_keywords_count: normalizedKeywords.values.length,
          update_frequency: updateFrequency || "每周",
          language_preference: languagePreference || null,
        },
      }).catch(() => undefined);
      setStatus("资料、画像、偏好和推送设置已保存");
      onReload();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSaving(false);
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
          <div className="flex flex-col gap-4 rounded-md border bg-muted/20 p-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 overflow-hidden rounded-md border bg-background">
                {profile.avatar_url ? (
                  <img src={profile.avatar_url} alt={profile.nickname || "头像"} className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-lg font-semibold text-muted-foreground">
                    {(profile.nickname || "研").slice(0, 1)}
                  </div>
                )}
              </div>
              <div>
                <div className="font-medium">头像与语音偏好</div>
                <div className="mt-1 text-sm text-muted-foreground">对应小程序头像上传和语音录入偏好。</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <input
                ref={avatarInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(event) => handleAvatarUpload(event.target.files?.[0])}
              />
              <input
                ref={audioInputRef}
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={(event) => handlePreferenceAudio(event.target.files?.[0])}
              />
              <Button size="sm" variant="outline" onClick={() => avatarInputRef.current?.click()} disabled={uploading}>
                <Upload className="mr-2 h-4 w-4" />
                上传头像
              </Button>
              <Button size="sm" variant="outline" onClick={() => audioInputRef.current?.click()} disabled={uploading}>
                <Mic className="mr-2 h-4 w-4" />
                语音偏好
              </Button>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>昵称</Label>
              <Input value={nickname} onChange={(event) => setNickname(event.target.value)} placeholder="用于研报小程序展示" />
            </div>
            <div className="space-y-2">
              <Label>职业 / 身份</Label>
              <Input value={occupation} onChange={(event) => setOccupation(event.target.value)} placeholder="例如：二级市场研究、品牌投资人" />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>关注行业 / 入门画像行业</Label>
              <Textarea value={industries} onChange={(event) => setIndustries(event.target.value)} placeholder="消费、科技、医药" />
              <div className="flex flex-wrap gap-2">
                {profile.options.industries.slice(0, 8).map((item) => (
                  <Button key={item} type="button" size="sm" variant="outline" onClick={() => mutatePreferenceTag("industry", item, "add")} disabled={uploading}>
                    + {item}
                  </Button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label>主题</Label>
              <Textarea value={themes} onChange={(event) => setThemes(event.target.value)} placeholder="AI、出海、周期" />
              <div className="flex flex-wrap gap-2">
                {profile.options.themes.slice(0, 8).map((item) => (
                  <Button key={item} type="button" size="sm" variant="outline" onClick={() => mutatePreferenceTag("theme", item, "add")} disabled={uploading}>
                    + {item}
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>更新频率</Label>
              <div className="flex flex-wrap gap-2">
                {(profile.options.update_frequencies.length ? profile.options.update_frequencies : ["每日", "每周"]).map((item) => (
                  <Button
                    key={item}
                    type="button"
                    size="sm"
                    variant={updateFrequency === item ? "secondary" : "outline"}
                    onClick={() => setUpdateFrequency(item)}
                  >
                    {item}
                  </Button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label>语言偏好</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={languagePreference}
                onChange={(event) => setLanguagePreference(event.target.value)}
              >
                <option value="">跟随内容</option>
                {profile.options.language_preferences.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>自定义关键词</Label>
            <Input value={keywords} onChange={(event) => setKeywords(event.target.value)} placeholder="用逗号或空格分隔，最多 10 个" />
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                value={keywordDraft}
                maxLength={60}
                onChange={(event) => setKeywordDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") appendKeywords(keywordDraft);
                }}
                placeholder="输入一个关注点后添加"
              />
              <Button type="button" variant="outline" onClick={() => appendKeywords(keywordDraft)}>
                添加
              </Button>
            </div>
            <div className="text-xs text-muted-foreground">最多 10 个标签，已选 {splitTags(keywords).length}/10。</div>
            <div className="flex flex-wrap gap-2">
              {splitTags(keywords).slice(0, 12).map((item) => (
                <Button key={item} type="button" size="sm" variant="secondary" onClick={() => mutatePreferenceTag("custom_keyword", item, "remove")} disabled={uploading}>
                  {item}
                  <X className="ml-2 h-3 w-3" />
                </Button>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <Label>自定义推荐要求</Label>
            <div className="grid gap-2 md:grid-cols-4">
              {PROMPT_TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => {
                    setCustomPrompt(template.prompt);
                    setStatus(`已应用模板：${template.title}`);
                  }}
                  className={`rounded-md border p-3 text-left text-sm transition-colors hover:bg-muted/40 ${customPrompt.trim() === template.prompt ? "border-primary bg-muted/50" : ""}`}
                >
                  <span className="block font-medium">{template.title}</span>
                  <span className="mt-1 block text-xs leading-5 text-muted-foreground">{template.description}</span>
                </button>
              ))}
            </div>
            <Textarea
              value={customPrompt}
              maxLength={500}
              onChange={(event) => setCustomPrompt(event.target.value)}
              placeholder="例如：更关注商业模式和估值变化"
            />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <button type="button" className="hover:text-foreground" onClick={() => setCustomPrompt("")}>
                清空自定义
              </button>
              <span>{customPrompt.length}/500</span>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-3 rounded-md border p-3 text-sm">
              <input
                type="checkbox"
                checked={deliveryEnabled}
                onChange={(event) => setDeliveryEnabled(event.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <span>
                <span className="block font-medium">接收小程序/公众号推送</span>
                <span className="text-muted-foreground">对应小程序投递订阅设置。</span>
              </span>
            </label>
            <div className="space-y-2">
              <Label>订阅状态</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={subscriptionStatus}
                onChange={(event) => setSubscriptionStatus(event.target.value)}
              >
                <option value="accept">accept</option>
                <option value="reject">reject</option>
                <option value="ban">ban</option>
                <option value="unknown">unknown</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={save} disabled={saving || uploading}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              保存资料与偏好
            </Button>
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
  const [recommendationMode, setRecommendationMode] = useState<"public" | "personalized">("public");
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [freshness, setFreshness] = useState<ReportFreshness | null>(null);
  const [homeFeed, setHomeFeed] = useState<DigestDetail | null>(null);
  const [notifications, setNotifications] = useState<NotificationResponse | null>(null);
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [billing, setBilling] = useState<BillingOverview | null>(null);
  const [invite, setInvite] = useState<InviteOverview | null>(null);
  const [catalog, setCatalog] = useState<ProductItem[]>([]);
  const [officialBinding, setOfficialBinding] = useState<OfficialBindingStatus | null>(null);
  const [mall, setMall] = useState<PointsMallResponse | null>(null);
  const [archive, setArchive] = useState<HedgeFundArchiveResponse | null>(null);
  const [activeFundId, setActiveFundId] = useState("");
  const [activeHoldingMarket, setActiveHoldingMarket] = useState("US");
  const [holdings, setHoldings] = useState<HedgeFundHoldingsResponse | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);

  async function loadPublic() {
    setLoadingRecommendations(true);
    try {
      const [nextRecommendations, nextArchive, nextFreshness] = await Promise.all([
        getRecommendations(12, recommendationMode),
        getHedgeFundArchive(),
        getReportFreshness().catch(() => null),
      ]);
      setRecommendations(nextRecommendations);
      setArchive(nextArchive);
      setFreshness(nextFreshness);
      setErrors((prev) => ({ ...prev, reports: "", funds: "" }));
      const firstFund = nextArchive.funds[0];
      if (firstFund) {
        setActiveFundId(firstFund.id);
        setActiveHoldingMarket("US");
        getHedgeFundHoldings(firstFund.id, "US").then(setHoldings).catch(() => setHoldings(null));
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
      const [feed, notice, user, overview, inviteOverview, productCatalog, binding, pointsMall] = await Promise.all([
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
        getInviteOverview().catch(() => null),
        getBillingCatalog().catch(() => ({ items: [] })),
        getOfficialBindingStatus().catch(() => null),
        getPointsMall().catch((error) => {
          nextErrors.mall = error instanceof Error ? error.message : "积分商城加载失败";
          return null;
        }),
      ]);
      setHomeFeed(feed);
      setNotifications(notice);
      setProfile(user);
      setBilling(overview);
      setInvite(inviteOverview);
      setCatalog(productCatalog?.items || []);
      setOfficialBinding(binding);
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
    trackClientEvent({
      event_name: "web_research_opened",
      page_path: "/research",
      metadata: { tab: tab || "reports" },
    }).catch(() => undefined);
    loadPublic();
    loadPrivate();
  }, []);

  function refreshAll() {
    loadPublic();
    loadPrivate();
  }

  function changeRecommendationMode(mode: "public" | "personalized") {
    setRecommendationMode(mode);
    setLoadingRecommendations(true);
    getRecommendations(12, mode)
      .then((data) => {
        setRecommendations(data);
        setErrors((prev) => ({ ...prev, reports: "" }));
      })
      .catch((error) => {
        setErrors((prev) => ({ ...prev, reports: error instanceof Error ? error.message : "推荐研报加载失败" }));
      })
      .finally(() => setLoadingRecommendations(false));
  }

  async function selectFund(fund: HedgeFundArchiveFund) {
    setActiveFundId(fund.id);
    setActiveHoldingMarket("US");
    setHoldings(null);
    try {
      setHoldings(await getHedgeFundHoldings(fund.id, "US"));
      setErrors((prev) => ({ ...prev, funds: "" }));
    } catch (error) {
      setErrors((prev) => ({ ...prev, funds: error instanceof Error ? error.message : "持仓加载失败" }));
    }
  }

  async function selectHoldingMarket(market: string) {
    if (!activeFundId) return;
    const normalized = market.trim().toUpperCase() || "US";
    setActiveHoldingMarket(normalized);
    setHoldings(null);
    try {
      setHoldings(await getHedgeFundHoldings(activeFundId, normalized));
      setErrors((prev) => ({ ...prev, funds: "" }));
    } catch (error) {
      setErrors((prev) => ({ ...prev, funds: error instanceof Error ? error.message : "持仓加载失败" }));
    }
  }

  async function downloadFundMiniappCode(fundId: string) {
    try {
      await downloadHedgeFundMiniappCode(fundId);
      trackClientEvent({
        event_name: "web_hedge_fund_miniapp_code_downloaded",
        page_path: "/research?tab=funds",
        metadata: { fund_id: fundId },
      }).catch(() => undefined);
      setErrors((prev) => ({ ...prev, funds: "" }));
    } catch (error) {
      setErrors((prev) => ({ ...prev, funds: error instanceof Error ? error.message : "小程序码下载失败" }));
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

  async function refreshDigestNotifications() {
    try {
      const notice = await refreshNotifications(20);
      setNotifications(notice);
      setErrors((prev) => ({ ...prev, digests: "" }));
    } catch (error) {
      setErrors((prev) => ({ ...prev, digests: error instanceof Error ? error.message : "通知刷新失败" }));
    }
  }

  async function readNotification(id: number) {
    try {
      await markNotificationRead(id);
      const notice = await getNotifications(20);
      setNotifications(notice);
    } catch (error) {
      setErrors((prev) => ({ ...prev, digests: error instanceof Error ? error.message : "标记已读失败" }));
    }
  }

  async function readAllNotifications() {
    try {
      await markAllNotificationsRead();
      const notice = await getNotifications(20);
      setNotifications(notice);
    } catch (error) {
      setErrors((prev) => ({ ...prev, digests: error instanceof Error ? error.message : "全部已读失败" }));
    }
  }

  async function createOrderForProduct(product: ProductItem) {
    try {
      const order = await createBillingOrder({ product_code: product.code });
      const payment = await prepareBillingOrderPayment(order.id);
      const suffix = payment.already_paid
        ? "订单已支付"
        : payment.configured === false
          ? payment.message || "支付暂未配置"
          : payment.message || "订单已创建，请在小程序内完成微信支付";
      alert(`${order.title}\n${formatMoneyFen(order.amount_fen)}\n${suffix}`);
      const overview = await getBillingOverview();
      setBilling(overview);
    } catch (error) {
      setErrors((prev) => ({ ...prev, membership: error instanceof Error ? error.message : "创建订单失败" }));
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
            <ReportsPanel
              data={recommendations}
              freshness={freshness}
              mode={recommendationMode}
              loading={loadingRecommendations}
              error={errors.reports || ""}
              onReload={loadPublic}
              onModeChange={changeRecommendationMode}
            />
          </TabsContent>
          <TabsContent value="digests">
            <DigestsPanel
              feed={homeFeed}
              notifications={notifications}
              error={errors.digests || ""}
              onReload={loadPrivate}
              onRefreshNotifications={refreshDigestNotifications}
              onMarkRead={readNotification}
              onMarkAllRead={readAllNotifications}
            />
          </TabsContent>
          <TabsContent value="funds">
            <FundsPanel
              archive={archive}
              holdings={holdings}
              activeFundId={activeFundId}
              activeMarket={activeHoldingMarket}
              error={errors.funds || ""}
              onSelectFund={selectFund}
              onSelectMarket={selectHoldingMarket}
              onDownloadMiniappCode={downloadFundMiniappCode}
            />
          </TabsContent>
          <TabsContent value="mall">
            <MallPanel mall={mall} error={errors.mall || ""} onReload={loadPrivate} />
          </TabsContent>
          <TabsContent value="membership">
            <MembershipPanel
              overview={billing}
              profile={profile}
              invite={invite}
              catalog={catalog}
              officialBinding={officialBinding}
              error={errors.membership || errors.profile || ""}
              onCheckIn={checkIn}
              onReload={loadPrivate}
              onCreateOrder={createOrderForProduct}
            />
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
