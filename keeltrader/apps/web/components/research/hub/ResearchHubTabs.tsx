"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DigestsPanel,
  FeedbackPanel,
  FundsPanel,
  MallPanel,
  MembershipPanel,
  PreferencesPanel,
  ReportsPanel,
} from "@/components/research/hub/panels";
import { MODULES } from "@/components/research/hub/constants";
import { type TabValue } from "@/components/research/hub/types";
import type {
  BillingOrderDetail,
  BillingOverview,
  DigestDetail,
  HedgeFundArchiveFund,
  HedgeFundArchiveResponse,
  HedgeFundHoldingsResponse,
  InviteOverview,
  NotificationResponse,
  OfficialBindingStatus,
  PointsMallResponse,
  PreferenceOptionsResponse,
  ProductItem,
  RecommendationResponse,
  ReportFreshness,
  UserProfileResponse,
} from "@/lib/research-api";

type RecommendationMode = "public" | "personalized";

export function ResearchHubTabs({
  activeTab,
  onActiveTabChange,
  recommendations,
  freshness,
  recommendationMode,
  loadingRecommendations,
  homeFeed,
  notifications,
  profile,
  billing,
  invite,
  catalog,
  officialBinding,
  preferenceOptions,
  orderDetail,
  orderStatus,
  mall,
  archive,
  holdings,
  activeFundId,
  activeHoldingMarket,
  activeHoldingPeriod,
  errors,
  onLoadPublic,
  onLoadPrivate,
  onRecommendationModeChange,
  onRefreshNotifications,
  onMarkNotificationRead,
  onMarkAllNotificationsRead,
  onSelectFund,
  onSelectHoldingMarket,
  onSelectHoldingPeriod,
  onDownloadFundMiniappCode,
  onCheckIn,
  onCreateOrder,
  onOpenOrder,
  onRefreshOrderPayment,
}: {
  activeTab: TabValue;
  onActiveTabChange: (value: TabValue) => void;
  recommendations: RecommendationResponse | null;
  freshness: ReportFreshness | null;
  recommendationMode: RecommendationMode;
  loadingRecommendations: boolean;
  homeFeed: DigestDetail | null;
  notifications: NotificationResponse | null;
  profile: UserProfileResponse | null;
  billing: BillingOverview | null;
  invite: InviteOverview | null;
  catalog: ProductItem[];
  officialBinding: OfficialBindingStatus | null;
  preferenceOptions: PreferenceOptionsResponse | null;
  orderDetail: BillingOrderDetail | null;
  orderStatus: string;
  mall: PointsMallResponse | null;
  archive: HedgeFundArchiveResponse | null;
  holdings: HedgeFundHoldingsResponse | null;
  activeFundId: string;
  activeHoldingMarket: string;
  activeHoldingPeriod: string;
  errors: Record<string, string>;
  onLoadPublic: (mode?: RecommendationMode) => void | Promise<void>;
  onLoadPrivate: () => void | Promise<void>;
  onRecommendationModeChange: (mode: RecommendationMode) => void;
  onRefreshNotifications: () => void | Promise<void>;
  onMarkNotificationRead: (id: number) => void | Promise<void>;
  onMarkAllNotificationsRead: () => void | Promise<void>;
  onSelectFund: (fund: HedgeFundArchiveFund) => void | Promise<void>;
  onSelectHoldingMarket: (market: string) => void | Promise<void>;
  onSelectHoldingPeriod: (period: string) => void | Promise<void>;
  onDownloadFundMiniappCode: (fundId: string) => void | Promise<void>;
  onCheckIn: () => void | Promise<void>;
  onCreateOrder: (product: ProductItem) => void | Promise<void>;
  onOpenOrder: (orderId: number) => void | Promise<void>;
  onRefreshOrderPayment: (orderId: number) => void | Promise<void>;
}) {
  return (
    <Tabs value={activeTab} onValueChange={(value) => onActiveTabChange(value as TabValue)} className="space-y-5">
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
          onReload={onLoadPublic}
          onModeChange={onRecommendationModeChange}
        />
      </TabsContent>
      <TabsContent value="digests">
        <DigestsPanel
          feed={homeFeed}
          notifications={notifications}
          profile={profile}
          publicItems={recommendations?.items || []}
          error={errors.digests || ""}
          onReload={onLoadPrivate}
          onRefreshNotifications={onRefreshNotifications}
          onMarkRead={onMarkNotificationRead}
          onMarkAllRead={onMarkAllNotificationsRead}
          onGoPreferences={() => onActiveTabChange("preferences")}
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
          onSelectFund={onSelectFund}
          onSelectMarket={onSelectHoldingMarket}
          onSelectPeriod={onSelectHoldingPeriod}
          onDownloadMiniappCode={onDownloadFundMiniappCode}
        />
      </TabsContent>
      <TabsContent value="mall">
        <MallPanel mall={mall} error={errors.mall || ""} onReload={onLoadPrivate} />
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
          onCheckIn={onCheckIn}
          onReload={onLoadPrivate}
          onCreateOrder={onCreateOrder}
          onOpenOrder={onOpenOrder}
          onRefreshOrderPayment={onRefreshOrderPayment}
          onGoMall={() => onActiveTabChange("mall")}
        />
      </TabsContent>
      <TabsContent value="preferences">
        <PreferencesPanel profile={profile} preferenceOptions={preferenceOptions} error={errors.profile || ""} onReload={onLoadPrivate} />
      </TabsContent>
      <TabsContent value="feedback">
        <FeedbackPanel />
      </TabsContent>
    </Tabs>
  );
}
