"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, RefreshCw, Sparkles, Star } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AuthBridge,
  DigestsPanel,
  FeedbackPanel,
  FundsPanel,
  MallPanel,
  MembershipPanel,
  PreferencesPanel,
  ReportsPanel,
} from "@/components/research/hub/panels";
import { MODULES } from "@/components/research/hub/constants";
import { formatMoneyFen, officialArticleEventName } from "@/components/research/hub/formatters";
import { type TabValue } from "@/components/research/hub/types";
import {
  captureOfficialArticleAttribution,
  createBillingOrder,
  dailyCheckIn,
  downloadHedgeFundMiniappCode,
  getBillingCatalog,
  getBillingOrder,
  getBillingOverview,
  getHedgeFundArchive,
  getHedgeFundHoldings,
  getHomeFeed,
  getInviteOverview,
  getNotifications,
  getOfficialBindingStatus,
  getPointsMall,
  getPointsMallCatalog,
  getPreferenceOptions,
  getRecommendations,
  getReportFreshness,
  getUserProfile,
  markAllNotificationsRead,
  markNotificationRead,
  prepareBillingOrderPayment,
  refreshNotifications,
  savePendingInviteFromParams,
  trackClientEvent,
  type BillingOrderDetail,
  type BillingOverview,
  type DigestDetail,
  type HedgeFundArchiveFund,
  type HedgeFundArchiveResponse,
  type HedgeFundHoldingsResponse,
  type InviteOverview,
  type NotificationResponse,
  type OfficialBindingStatus,
  type PointsMallResponse,
  type PreferenceOptionsResponse,
  type ProductItem,
  type RecommendationResponse,
  type ReportFreshness,
  type UserProfileResponse,
} from "@/lib/research-api";

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
  const [preferenceOptions, setPreferenceOptions] = useState<PreferenceOptionsResponse | null>(null);
  const [orderDetail, setOrderDetail] = useState<BillingOrderDetail | null>(null);
  const [orderStatus, setOrderStatus] = useState("");
  const [mall, setMall] = useState<PointsMallResponse | null>(null);
  const [archive, setArchive] = useState<HedgeFundArchiveResponse | null>(null);
  const [activeFundId, setActiveFundId] = useState("");
  const [activeHoldingMarket, setActiveHoldingMarket] = useState("US");
  const [activeHoldingPeriod, setActiveHoldingPeriod] = useState("");
  const [holdings, setHoldings] = useState<HedgeFundHoldingsResponse | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);

  const loadPublic = useCallback(async (mode: "public" | "personalized" = "public") => {
    setLoadingRecommendations(true);
    try {
      const [nextRecommendations, nextArchive, nextFreshness] = await Promise.all([
        getRecommendations(12, mode),
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
        setActiveHoldingPeriod("");
        getHedgeFundHoldings(firstFund.id, "US").then(setHoldings).catch(() => setHoldings(null));
      }
    } catch (error) {
      setErrors((prev) => ({ ...prev, reports: error instanceof Error ? error.message : "公共内容加载失败" }));
    } finally {
      setLoadingRecommendations(false);
    }
  }, []);

  const loadPrivate = useCallback(async () => {
    const nextErrors: Record<string, string> = {};
    try {
      const [feed, notice, user, overview, inviteOverview, productCatalog, binding, preferenceOptionData, pointsMall] = await Promise.all([
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
        getPreferenceOptions().catch(() => null),
        getPointsMall().catch(() => getPointsMallCatalog().catch((error) => {
          nextErrors.mall = error instanceof Error ? error.message : "积分商城加载失败";
          return null;
        })),
      ]);
      setHomeFeed(feed);
      setNotifications(notice);
      setProfile(user);
      setBilling(overview);
      setInvite(inviteOverview);
      setCatalog(productCatalog?.items || []);
      setOfficialBinding(binding);
      setPreferenceOptions(preferenceOptionData);
      setMall(pointsMall);
    } finally {
      setErrors((prev) => ({ ...prev, ...nextErrors }));
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get("tab") as TabValue | null;
    const effectiveTab = tab && MODULES.some((item) => item.value === tab) ? tab : "reports";
    if (effectiveTab !== "reports") {
      setActiveTab(effectiveTab);
    }
    const attribution = captureOfficialArticleAttribution(params);
    if (attribution) {
      trackClientEvent({
        event_name: officialArticleEventName(effectiveTab, attribution.entry),
        page_path: "/research",
        status: "success",
        metadata: {
          source: attribution.source,
          campaign_key: attribution.campaign_key,
          article_type: attribution.article_type,
          entry: attribution.entry,
          tab: effectiveTab,
        },
      }).catch(() => undefined);
    }
    const pendingInvite = savePendingInviteFromParams(params, "research_web_share", effectiveTab);
    if (pendingInvite) {
      trackClientEvent({
        event_name: "web_pending_invite_captured",
        page_path: "/research",
        status: "success",
        metadata: {
          inviter_user_id: pendingInvite.inviter_user_id || null,
          invite_code: pendingInvite.invite_code || "",
          source_type: pendingInvite.source_type,
          source_id: pendingInvite.source_id,
          tab: effectiveTab,
        },
      }).catch(() => undefined);
    }
    trackClientEvent({
      event_name: "web_research_opened",
      page_path: "/research",
      metadata: { tab: effectiveTab },
    }).catch(() => undefined);
    loadPublic("public");
    loadPrivate();
  }, [loadPrivate, loadPublic]);

  function refreshAll() {
    loadPublic(recommendationMode);
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
    setActiveHoldingPeriod("");
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
    setActiveHoldingPeriod("");
    setHoldings(null);
    try {
      setHoldings(await getHedgeFundHoldings(activeFundId, normalized));
      setErrors((prev) => ({ ...prev, funds: "" }));
    } catch (error) {
      setErrors((prev) => ({ ...prev, funds: error instanceof Error ? error.message : "持仓加载失败" }));
    }
  }

  async function selectHoldingPeriod(period: string) {
    if (!activeFundId) return;
    const normalized = period.trim();
    setActiveHoldingPeriod(normalized);
    setHoldings(null);
    try {
      setHoldings(await getHedgeFundHoldings(activeFundId, activeHoldingMarket, normalized));
      setErrors((prev) => ({ ...prev, funds: "" }));
    } catch (error) {
      setErrors((prev) => ({ ...prev, funds: error instanceof Error ? error.message : "披露期加载失败" }));
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
      setOrderDetail(order);
      setOrderStatus(`${formatMoneyFen(order.amount_fen)} · ${suffix}`);
      const overview = await getBillingOverview();
      setBilling(overview);
    } catch (error) {
      setErrors((prev) => ({ ...prev, membership: error instanceof Error ? error.message : "创建订单失败" }));
    }
  }

  async function openOrder(orderId: number) {
    if (!orderId) {
      setOrderDetail(null);
      setOrderStatus("");
      return;
    }
    setOrderStatus("加载订单详情...");
    try {
      const detail = await getBillingOrder(orderId);
      setOrderDetail(detail);
      setOrderStatus("");
      setErrors((prev) => ({ ...prev, membership: "" }));
    } catch (error) {
      setOrderStatus(error instanceof Error ? error.message : "订单详情加载失败");
    }
  }

  async function refreshOrderPayment(orderId: number) {
    setOrderStatus("正在刷新支付状态...");
    try {
      const payment = await prepareBillingOrderPayment(orderId);
      const detail = await getBillingOrder(orderId);
      setOrderDetail(detail);
      setOrderStatus(payment.already_paid ? "订单已支付，权益已生效" : payment.message || "支付状态已刷新");
      const overview = await getBillingOverview();
      setBilling(overview);
    } catch (error) {
      setOrderStatus(error instanceof Error ? error.message : "支付状态刷新失败");
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
              profile={profile}
              publicItems={recommendations?.items || []}
              error={errors.digests || ""}
              onReload={loadPrivate}
              onRefreshNotifications={refreshDigestNotifications}
              onMarkRead={readNotification}
              onMarkAllRead={readAllNotifications}
              onGoPreferences={() => setActiveTab("preferences")}
            />
          </TabsContent>
          <TabsContent value="funds">
            <FundsPanel
              archive={archive}
              holdings={holdings}
              activeFundId={activeFundId}
              activeMarket={activeHoldingMarket}
              activePeriod={activeHoldingPeriod}
              error={errors.funds || ""}
              onSelectFund={selectFund}
              onSelectMarket={selectHoldingMarket}
              onSelectPeriod={selectHoldingPeriod}
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
              orderDetail={orderDetail}
              orderStatus={orderStatus}
              error={errors.membership || errors.profile || ""}
              onCheckIn={checkIn}
              onReload={loadPrivate}
              onCreateOrder={createOrderForProduct}
              onOpenOrder={openOrder}
              onRefreshOrderPayment={refreshOrderPayment}
              onGoMall={() => setActiveTab("mall")}
            />
          </TabsContent>
          <TabsContent value="preferences">
            <PreferencesPanel profile={profile} preferenceOptions={preferenceOptions} error={errors.profile || ""} onReload={loadPrivate} />
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
