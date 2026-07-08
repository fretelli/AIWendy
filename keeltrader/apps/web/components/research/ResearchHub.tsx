"use client";

import { useCallback, useEffect, useState } from "react";

import { AuthBridge } from "@/components/research/hub/panels";
import { MODULES } from "@/components/research/hub/constants";
import { ResearchHubFooter, ResearchHubHeader, ResearchModuleGrid } from "@/components/research/hub/ResearchHubChrome";
import { ResearchHubTabs } from "@/components/research/hub/ResearchHubTabs";
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
        <ResearchHubHeader onRefresh={refreshAll} />

        <ResearchModuleGrid activeTab={activeTab} onChange={setActiveTab} />

        <AuthBridge onSaved={refreshAll} />

        <ResearchHubTabs
          activeTab={activeTab}
          onActiveTabChange={setActiveTab}
          recommendations={recommendations}
          freshness={freshness}
          recommendationMode={recommendationMode}
          loadingRecommendations={loadingRecommendations}
          homeFeed={homeFeed}
          notifications={notifications}
          profile={profile}
          billing={billing}
          invite={invite}
          catalog={catalog}
          officialBinding={officialBinding}
          preferenceOptions={preferenceOptions}
          orderDetail={orderDetail}
          orderStatus={orderStatus}
          mall={mall}
          archive={archive}
          holdings={holdings}
          activeFundId={activeFundId}
          activeHoldingMarket={activeHoldingMarket}
          activeHoldingPeriod={activeHoldingPeriod}
          errors={errors}
          onLoadPublic={loadPublic}
          onLoadPrivate={loadPrivate}
          onRecommendationModeChange={changeRecommendationMode}
          onRefreshNotifications={refreshDigestNotifications}
          onMarkNotificationRead={readNotification}
          onMarkAllNotificationsRead={readAllNotifications}
          onSelectFund={selectFund}
          onSelectHoldingMarket={selectHoldingMarket}
          onSelectHoldingPeriod={selectHoldingPeriod}
          onDownloadFundMiniappCode={downloadFundMiniappCode}
          onCheckIn={checkIn}
          onCreateOrder={createOrderForProduct}
          onOpenOrder={openOrder}
          onRefreshOrderPayment={refreshOrderPayment}
        />

        <ResearchHubFooter />
      </div>
    </div>
  );
}
