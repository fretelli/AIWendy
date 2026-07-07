"use client";

export type ApiErrorPayload =
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

export type ReportFreshness = {
  today: string;
  week_start?: string;
  latest_report_date: string | null;
  report_date_lag_days: number | null;
  today_report_count: number;
  current_week_report_count: number;
  completed_count: number;
  partial_count: number;
  ocr_backlog_count: number;
  latest_created_at: string | null;
  created_last_24h_count: number;
  sources?: Array<{
    source_family: string;
    latest_report_date: string | null;
    latest_created_at: string | null;
    today_report_count: number;
    current_week_report_count: number;
    completed_count: number;
    partial_count: number;
    ocr_backlog_count: number;
  }>;
  ingest_queue?: {
    pending: number;
    processing: number;
    failed: number;
    oldest_active_created_at: string | null;
  };
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

export type PreferenceOptionsResponse = {
  options: {
    industries: string[];
    themes: string[];
    update_frequencies: string[];
    language_preferences?: string[];
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

export type InviteOverview = {
  invite_code: string;
  summary: {
    invited_count: number;
    rewarded_count: number;
    reward_copy: string;
    share_message?: string;
    invite_landing_path?: string;
    reward_rule?: {
      reward_type: string;
      inviter_points?: number;
      invitee_points?: number;
      valid_days?: number;
      display_text: string;
    };
    pdf_credits?: {
      total: number;
      remaining: number;
    };
    invite_points?: {
      total: number;
      remaining: number;
    };
  };
  records: Array<{
    id: number;
    invite_code: string;
    source_type: string;
    source_id: string | null;
    status: string;
    rewarded_at: string | null;
    created_at: string | null;
    invited_nickname: string;
    rewards: Array<{
      id: number;
      user_id: number;
      reward_type: string;
      reward_value: Record<string, unknown>;
      status: string;
      expires_at: string | null;
    }>;
  }>;
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

export type UserPreferenceTagType = "industry" | "theme" | "custom_keyword";

export type ClientEventPayload = {
  event_name: string;
  page_path?: string;
  status?: "info" | "warning" | "error" | string;
  message?: string;
  report_id?: string;
  digest_id?: number;
  metadata?: Record<string, unknown>;
};

export type WebOfficialArticleAttribution = {
  source: string;
  campaign_key: string;
  article_type: string;
  entry: string;
  captured_at: number;
};

export type PendingInvite = {
  inviter_user_id: number;
  invite_code?: string;
  source_type: string;
  source_id: string;
  captured_at: number;
};
