"use client";

type ApiErrorPayload =
  | { detail?: unknown }
  | { error?: { message?: string } };

export type ReportCardItem = {
  id: string;
  title: string;
  display_title?: string | null;
  broker?: string;
  language?: string;
  report_date?: string;
  ingested_at?: string;
  ingest_status?: string;
  source_url?: string;
  pdf_url?: string;
  has_pdf?: boolean;
  brief?: string;
  summary?: string;
  formal_overview?: string;
  reason?: string;
  tags?: string[];
  company_names?: string[];
  primary_company_name?: string | null;
  subject_companies?: string[];
  subject_label?: string | null;
  subject_confidence?: string | null;
};

export type ReportDetail = ReportCardItem & {
  doc_type?: string;
  source_note?: string;
  sections?: Array<{ id: string; granularity?: string; content?: string }>;
  note?: {
    card_brief?: string;
    overview?: string;
    display_summary_points?: string[];
    key_points?: string[];
    risks?: string[];
    conclusion?: string;
    evidence_quotes?: Array<{ text?: string; page_number?: number | null }>;
  };
  display_summary_points?: string[];
  access?: {
    is_member: boolean;
    has_digest_purchase: boolean;
    has_pdf_purchase?: boolean;
    pdf_credit_count?: number;
    can_view_full_report: boolean;
    can_view_pdf?: boolean;
    membership_product_codes: string[];
    paywall_message: string;
  };
};

export type ReportNoteState = {
  status: "ready" | "processing" | "unavailable" | string;
  message: string;
  retry_after_seconds?: number | null;
  note?: ReportDetail["note"] | null;
};

export type ReportBriefingState = {
  status: "ready" | "processing" | "unavailable" | string;
  message: string;
  text: string;
  version: string;
  retry_after_seconds?: number;
  mime_type?: string;
  file_name?: string;
  audio_url?: string;
};

export type DigestDetail = {
  id: number;
  type: string;
  title: string;
  summary: string;
  body: string;
  created_at: string | null;
  is_read: boolean;
  mode: string;
  anchor: string;
  variant: string;
  is_current_period?: boolean;
  status?: string;
  fallback_message?: string;
  personalized_item_count?: number;
  public_item_count?: number;
  items: ReportCardItem[];
  access?: {
    is_member: boolean;
    has_digest_purchase: boolean;
    can_view_full_digest: boolean;
    can_view_history: boolean;
    unlocked_item_count: number;
    locked_items_count: number;
    membership_product_codes: string[];
    paywall_message: string;
  };
};

export type RecommendationResponse = {
  profile_completed: boolean;
  preferences: {
    industries: string[];
    themes: string[];
    update_frequency: string | null;
    language_preference: string | null;
    custom_keywords: string[];
    custom_prompt: string;
  };
  items: ReportCardItem[];
  from_cache?: boolean;
  generated_at?: string;
  latest_report_date?: string | null;
  refreshing?: boolean;
};

export type UserProfileResponse = {
  user_id: number;
  nickname: string;
  avatar_url: string;
  phone_bound: boolean;
  phone_masked: string;
  onboarding_completed: boolean;
  onboarding_profile: {
    industries: string[];
    occupation: string;
  };
  profile_completed: boolean;
  preferences: {
    industries: string[];
    themes: string[];
    update_frequency: string | null;
    language_preference: string | null;
    custom_keywords: string[];
    custom_prompt: string;
  };
  options: {
    industries: string[];
    themes: string[];
    update_frequencies: string[];
    language_preferences: string[];
  };
  delivery: {
    channel: string;
    enabled: boolean;
    subscription_status: string;
    last_subscribed_at: string | null;
    template_id: string;
    subscription_type?: string;
  };
};

export type BillingOverview = {
  active_membership: {
    is_active: boolean;
    entitlement_type: string | null;
    source: string | null;
    expires_at: string | null;
  };
  entitlements: Array<{
    id: number;
    entitlement_type: string;
    target_type: string | null;
    target_id: string | null;
    source: string | null;
    expires_at: string | null;
  }>;
  recent_orders: Array<{
    id: number;
    order_no: string;
    title: string;
    status: string;
    payment_status: string;
    amount_fen: number;
    currency: string;
    target_type: string | null;
    target_id: string | null;
    created_at: string | null;
    paid_at?: string | null;
  }>;
  invite_summary: {
    invite_code: string;
    invited_count: number;
    rewarded_count: number;
    reward_copy: string;
    share_message?: string;
  };
  points_mall?: {
    points: { total: number; remaining: number };
    item_count: number;
  };
  daily_checkin: {
    checked_in_today: boolean;
    reward_points: number;
    last_checkin_at: string | null;
  };
  payment_ready: boolean;
};

export type ProductItem = {
  id: number;
  code: string;
  name: string;
  product_type: string;
  target_type?: string | null;
  duration_days?: number | null;
  price_fen: number;
  original_price_fen: number;
  currency: string;
  benefits: Record<string, unknown>;
  is_active: boolean;
};

export type BillingOrderDetail = {
  id: number;
  order_no: string;
  title: string;
  order_type: string;
  target_type: string | null;
  target_id: string | null;
  amount_fen: number;
  currency: string;
  status: string;
  payment_provider?: string;
  payment_status: string;
  created_at: string | null;
  paid_at?: string | null;
};

export type OfficialBindingStatus = {
  bound: boolean;
  binding: {
    id: number;
    status: string;
    bind_source: string;
    official_openid_masked: string;
    subscribe_status: string;
    created_at: string | null;
  } | null;
};

export type PointsMallItem = {
  code: string;
  name: string;
  subtitle: string;
  category: string;
  points_cost: number;
  stock: number;
  cover_theme: string;
  cover_image?: string;
  description: string;
  can_redeem: boolean;
};

export type PointsRedemption = {
  id: number;
  item_code: string;
  item_name: string;
  points_cost: number;
  status: string;
  recipient_name: string;
  recipient_phone: string;
  shipping_address: string;
  created_at: string | null;
};

export type PointsMallResponse = {
  points: { total: number; remaining: number };
  items: PointsMallItem[];
  redemptions: PointsRedemption[];
};

export type NotificationResponse = {
  unread_count: number;
  history_unread_count: number;
  items: Array<{
    id: number;
    type: string;
    title: string;
    body: string;
    is_read: boolean;
    read_at: string | null;
    created_at: string | null;
    payload: {
      mode?: string;
      anchor?: string;
      generated_at?: string;
      items?: ReportCardItem[];
    };
  }>;
};

export type HedgeFundArchiveFund = {
  id: string;
  manager_id?: string | null;
  region_id?: string | null;
  name: string;
  name_zh?: string;
  legal_name: string;
  logo_text: string;
  founder_name: string;
  founder_title: string;
  founder_quote: string;
  portrait_traits: string;
  headquarters: string;
  core_strategy: string;
  latest_dynamic: string;
  founded: string;
  signature: string;
  source_coverage: string;
  institution_type?: string;
  institution_type_label?: string;
  accent: string;
  secondary: string;
  strategy_ids: string[];
  strategy_names: string[];
  latest_filing?: {
    source_name?: string | null;
    filing_type?: string | null;
    report_period?: string | null;
    filing_date?: string | null;
    source_url?: string | null;
  } | null;
  sort_order: number;
};

export type HedgeFundArchiveResponse = {
  regions: Array<{ id: string; name: string; display_name: string; description: string; fund_count?: number }>;
  strategies: Array<{ id: string; name: string; description: string; fund_count?: number }>;
  institution_types?: Array<{ id: string; name: string; fund_count?: number }>;
  funds: HedgeFundArchiveFund[];
  coverage_note: string;
};

export type HedgeFundHoldingsResponse = {
  fund: { id: string; name: string; source_coverage: string; institution_type?: string };
  available_markets?: Array<{ market: string; label: string; holding_count: number; latest_period?: string | null }>;
  active_market?: string | null;
  periods?: Array<{ report_period: string; holding_count: number; total_market_value_usd?: number | null; filing_date?: string | null }>;
  selected_period?: string | null;
  previous_period?: string | null;
  holdings: Array<{
    security_name: string;
    ticker?: string | null;
    shares?: number | null;
    market_value_usd?: number | null;
    portfolio_weight?: number | null;
    change_shares?: number | null;
    source_name?: string | null;
    filing_date?: string | null;
  }>;
  coverage_note: string;
};

export type FeedbackCreatePayload = {
  category: string;
  content: string;
  contact?: string;
  page_path?: string;
  report_id?: string | null;
  digest_id?: number | null;
  metadata?: Record<string, unknown>;
};

function getErrorMessage(payload: ApiErrorPayload): string | null {
  if ("detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
      const msg = (detail[0] as { msg?: unknown }).msg;
      if (typeof msg === "string") return msg;
    }
  }

  if ("error" in payload) {
    const msg = payload.error?.message;
    if (msg) return msg;
  }

  return null;
}

function getResearchToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("research_access_token") || localStorage.getItem("research_token") || "";
}

export function setResearchToken(token: string) {
  if (typeof window === "undefined") return;
  const normalized = token.trim();
  if (normalized) {
    localStorage.setItem("research_access_token", normalized);
  } else {
    localStorage.removeItem("research_access_token");
  }
}

function createSessionId() {
  if (typeof window === "undefined") return "web-server";
  const key = "research_web_session_id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const next = `web_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
  localStorage.setItem(key, next);
  return next;
}

async function researchRequest<T>(path: string, init: RequestInit = {}, options: { auth?: "required" | "optional" | "none" } = {}) {
  const token = getResearchToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", headers.get("Content-Type") || "application/json");
  headers.set("X-Session-ID", createSessionId());
  if (token && options.auth !== "none") {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`/api/research${path}`, {
    ...init,
    headers,
  });
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    const message =
      payload && typeof payload === "object"
        ? getErrorMessage(payload as ApiErrorPayload)
        : null;
    throw new Error(message || response.statusText || "请求失败");
  }

  return payload as T;
}

export function getPublicRecommendations(limit = 12) {
  return researchRequest<RecommendationResponse>(`/reports/recommendations?limit=${limit}&mode=public`, {}, { auth: "optional" });
}

export function getReportDetail(id: string, digestId?: string | number | null) {
  const suffix = digestId ? `?digest_id=${encodeURIComponent(String(digestId))}` : "";
  return researchRequest<ReportDetail>(`/reports/${encodeURIComponent(id)}${suffix}`, {}, { auth: "optional" });
}

export function getReportNoteState(id: string) {
  return researchRequest<ReportNoteState>(`/reports/${encodeURIComponent(id)}/note`, {}, { auth: "required" });
}

export function triggerReportNote(id: string) {
  return researchRequest<ReportNoteState>(`/reports/${encodeURIComponent(id)}/note`, {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function getHomeFeed() {
  return researchRequest<DigestDetail>("/home/feed", {}, { auth: "required" });
}

export function getDigestDetail(id: string | number) {
  return researchRequest<DigestDetail>(`/digests/${encodeURIComponent(String(id))}`, {}, { auth: "required" });
}

export function getNotifications(limit = 20) {
  return researchRequest<NotificationResponse>(`/notifications?limit=${limit}`, {}, { auth: "required" });
}

export function refreshNotifications(limit = 20) {
  return researchRequest<NotificationResponse & { ok: boolean }>(`/notifications/refresh?limit=${limit}`, {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function markNotificationRead(id: number) {
  return researchRequest<{ ok: boolean }>(`/notifications/${id}/read`, {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function markAllNotificationsRead() {
  return researchRequest<{ ok: boolean }>("/notifications/read-all", {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function getUserProfile() {
  return researchRequest<UserProfileResponse>("/user/profile", {}, { auth: "required" });
}

export function updateUserPreferences(data: UserProfileResponse["preferences"]) {
  return researchRequest<{ ok: boolean; profile_completed: boolean }>("/user/preferences", {
    method: "PUT",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function updateOnboardingProfile(data: { industries: string[]; occupation: string }) {
  return researchRequest<{
    ok: boolean;
    onboarding_completed: boolean;
    onboarding_profile: UserProfileResponse["onboarding_profile"];
  }>("/user/onboarding-profile", {
    method: "PUT",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function updateAccountProfile(data: { nickname: string }) {
  return researchRequest<{
    ok: boolean;
    user_id: number;
    nickname: string;
    avatar_url: string;
  }>("/user/account-profile", {
    method: "PUT",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function updateMiniappDeliveryProfile(data: {
  enabled: boolean;
  subscription_status: "accept" | "reject" | "ban" | "unknown" | string;
}) {
  return researchRequest<{
    ok: boolean;
    delivery: UserProfileResponse["delivery"];
  }>("/user/delivery/miniapp-subscription", {
    method: "POST",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function getBillingOverview() {
  return researchRequest<BillingOverview>("/billing/me", {}, { auth: "required" });
}

export function getBillingCatalog() {
  return researchRequest<{ items: ProductItem[] }>("/billing/catalog", {}, { auth: "required" });
}

export function createBillingOrder(data: {
  product_code: string;
  target_type?: string | null;
  target_id?: string | null;
}) {
  return researchRequest<BillingOrderDetail>("/billing/orders", {
    method: "POST",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function prepareBillingOrderPayment(orderId: number) {
  return researchRequest<{
    ok: boolean;
    already_paid?: boolean;
    provider?: string;
    configured?: boolean;
    message?: string;
    payment_params?: Record<string, unknown> | null;
  }>(`/billing/orders/${orderId}/pay`, {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function getOfficialBindingStatus() {
  return researchRequest<OfficialBindingStatus>("/user/official-binding", {}, { auth: "required" });
}

export function dailyCheckIn() {
  return researchRequest<{ ok: boolean; awarded: boolean; checked_in_today: boolean; points_awarded: number; remaining_points?: number; message: string; last_checkin_at: string | null }>("/billing/check-in", {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function getPointsMall() {
  return researchRequest<PointsMallResponse>("/billing/points-mall", {}, { auth: "required" });
}

export function redeemPointsMallItem(data: {
  item_code: string;
  recipient_name: string;
  recipient_phone: string;
  shipping_address: string;
}) {
  return researchRequest<{ ok: boolean; points: PointsMallResponse["points"]; redemption: PointsRedemption }>("/billing/points-mall/redeem", {
    method: "POST",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function getHedgeFundArchive() {
  return researchRequest<HedgeFundArchiveResponse>("/hedge-funds/archive", {}, { auth: "optional" });
}

export function getHedgeFundHoldings(fundId: string, market = "US") {
  return researchRequest<HedgeFundHoldingsResponse>(`/hedge-funds/${encodeURIComponent(fundId)}/holdings?market=${encodeURIComponent(market)}`, {}, { auth: "optional" });
}

export function submitFeedback(data: FeedbackCreatePayload) {
  return researchRequest<{ ok: boolean; id: number; message: string }>("/feedback", {
    method: "POST",
    body: JSON.stringify({
      ...data,
      contact: data.contact || "",
      page_path: data.page_path || "/research",
      report_id: data.report_id || "",
      digest_id: data.digest_id || null,
      client_version: "keeltrader-web",
      metadata: {
        source: "keeltrader_web",
        ...(data.metadata || {}),
      },
    }),
  }, { auth: "optional" });
}

export function synthesizeReportBriefing(reportId: string) {
  return researchRequest<ReportBriefingState>("/speech/report-briefing", {
    method: "POST",
    body: JSON.stringify({ report_id: reportId }),
  }, { auth: "required" });
}

export function getReportBriefingStatus(reportId: string) {
  return researchRequest<ReportBriefingState>(`/speech/report-briefing/${encodeURIComponent(reportId)}`, {}, { auth: "required" });
}

export async function downloadResearchFile(path: string, fallbackFileName: string) {
  const token = getResearchToken();
  const headers = new Headers();
  headers.set("X-Session-ID", createSessionId());
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`/api/research${path}`, { headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message =
      payload && typeof payload === "object"
        ? getErrorMessage(payload as ApiErrorPayload)
        : null;
    throw new Error(message || response.statusText || "下载失败");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const fileNameMatch = /filename="?([^";]+)"?/i.exec(disposition);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileNameMatch?.[1] || fallbackFileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
