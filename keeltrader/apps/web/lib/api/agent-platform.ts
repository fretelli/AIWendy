import { apiForm, apiJson } from "@/lib/api/client";

export type AgentModelProfile = {
  id: string;
  name: string;
  provider: string;
  model: string;
  key_prefix?: string;
};
export type AgentDefinition = {
  id: string;
  name: string;
  role: string;
  description?: string;
  model_profile_id: string;
  tool_names: string[];
};
export type AgentRun = {
  id: string;
  prompt: string;
  status: string;
  current_step: number;
  tokens_used: number;
  cost_used_usd: number;
  created_at: string;
};
export type InteractionMode = "ask" | "research" | "plan";
export type WorkspaceScope = "general" | "research" | "content" | "ops";
export type AgentSession = {
  id: string;
  agent_definition_id?: string;
  title: string;
  status: string;
  interaction_mode: InteractionMode;
  workspace_scope: WorkspaceScope;
  company_code?: string;
  summary?: string;
  context_tokens: number;
  is_pinned: boolean;
  archived_at?: string;
  last_message_at: string;
  created_at: string;
};
export type CompanySearchItem = {
  ts_code: string;
  symbol: string;
  name: string;
  industry?: string;
  area?: string;
  market?: string;
  list_date?: string;
};
export type WatchlistItem = {
  id: string;
  company_code: string;
  company_name: string;
  industry?: string;
  refresh_enabled: boolean;
  added_at: string;
};
export type CompanyDossier = {
  dossier?: {
    status: string;
    current_version: number;
    stale: boolean;
    last_refreshed_at?: string;
  };
  snapshot?: {
    company: Record<string, unknown>;
    metrics: Record<string, unknown>;
    industry_peer_medians: Record<string, unknown>;
    anomaly_flags: string[];
    evidence_status: string;
    evidence_shortage?: string;
  };
  diff?: Record<string, unknown>;
  evidence: Array<{
    id: string;
    source_type: string;
    citation: Record<string, unknown>;
  }>;
  versions: Array<{ id: string; version: number; created_at: string }>;
};
export type AgentMessage = {
  id: string;
  session_id: string;
  run_id?: string;
  role: "user" | "assistant" | "system";
  kind: string;
  status: string;
  content: string;
  metadata_json?: Record<string, unknown>;
  created_at: string;
};
export type AgentApproval = {
  id: string;
  kind: string;
  preview: Record<string, unknown>;
  created_at: string;
};
export type AgentMemory = {
  id: string;
  key: string;
  value: unknown;
  confidence: number;
  version: number;
  is_deleted: boolean;
};
export type GlobalLearningMemory = {
  memory_id: string;
  scope: string;
  kind: string;
  content: string;
  importance: number;
  status: string;
  created_at: string;
};
export type MCPServer = {
  id: string;
  name: string;
  url: string;
  status: string;
  tools_snapshot: Array<{ name: string; description?: string }>;
};
export type AgentSchedule = {
  id: string;
  agent_definition_id?: string;
  name: string;
  cron: string;
  timezone: string;
  prompt: string;
  enabled: boolean;
  next_run_at?: string;
};
export type AgentRunTrace = {
  run: AgentRun & { session_id: string; started_at?: string; finished_at?: string };
  steps: Array<{ id: string; sequence: number; agent_role: string; tool_name?: string; status: string; attempts: number; input_keys: string[]; output_summary: Record<string, unknown>; error?: string; started_at?: string; finished_at?: string }>;
  events: Array<{ id: number; type: string; payload: Record<string, unknown>; created_at: string }>;
  artifacts: Array<{ id: string; artifact_type: string; title: string; created_at: string }>;
  tushare_calls: Array<{ step_id: string; sequence: number; status: string; dataset?: string; capability?: string; requested_fields: string[]; filter_keys: string[]; output_summary: Record<string, unknown>; error?: string; started_at?: string; finished_at?: string }>;
  redaction: "safe_summary_only";
};
export type Usage = {
  today: { input_tokens: number; output_tokens: number; cost_usd: number };
  limits: { tokens: number; cost_usd: number };
};
export type HolderSearchItem = {
  holder_name: string;
  holder_type: string;
  stock_count: number;
  first_end_date?: string;
  last_end_date?: string;
  last_ann_date?: string;
  exact_match: boolean;
  identity_warning?: string;
};
export type HolderWatchItem = {
  id: string;
  holder_name: string;
  normalized_name: string;
  holder_type: string;
  aliases: string[];
  enabled: boolean;
  last_scanned_at?: string;
  identity_warning?: string;
  created_at: string;
};
export type HolderCostEstimate = {
  unit_cost: number;
  unit_cost_low: number;
  unit_cost_high: number;
  covered_shares: number;
  coverage_ratio: number;
  estimated_covered_cost: number;
  estimated_position_cost?: number;
  first_estimated_period?: string;
  last_estimated_period?: string;
  method: "qfq_disclosure_average_cost_ledger";
  disclaimer: string;
};
export type HolderPosition = {
  ts_code: string;
  company_name?: string;
  industry?: string;
  market?: string;
  end_date: string;
  ann_date?: string;
  matched_names?: string[];
  hold_amount?: number;
  hold_ratio?: number;
  hold_float_ratio?: number;
  hold_change?: number;
  cost_estimate?: HolderCostEstimate | null;
};
// Stable contract spelling used by downstream audits: side: 'buy' | 'sell' | 'possible_sell'
export type HolderPriceEstimate = {
  side: "buy" | "sell" | "possible_sell";
  window_start: string;
  window_end: string;
  first_trade_date?: string;
  last_trade_date?: string;
  low: number;
  high: number;
  volume_weighted_price: number;
  trading_days: number;
  changed_shares?: number;
  estimated_amount?: number;
  method: "qfq_close_volume_weighted_reporting_window";
  disclaimer: string;
};
export type HolderHistoryEvent = HolderPosition & {
  event_type:
    | "first_seen"
    | "new"
    | "increased"
    | "reduced"
    | "unchanged"
    | "exited_top10";
  previous_end_date?: string;
  previous_hold_amount?: number;
  previous_hold_ratio?: number;
  previous_hold_float_ratio?: number;
  present: boolean;
  price_estimate?: HolderPriceEstimate | null;
};
export type HolderInboxEvent = {
  id: string;
  watch_id: string;
  ts_code: string;
  company_name?: string;
  holder_name: string;
  holder_type: string;
  event_type: HolderHistoryEvent["event_type"];
  end_date: string;
  ann_date?: string;
  previous_end_date?: string;
  values: Record<string, unknown>;
  read_at?: string;
  detected_at: string;
};
export type MarketSourceFreshness = {
  available: boolean;
  as_of?: string;
  lag_days?: number;
  lag_calendar_days?: number;
  lag_trading_days?: number;
  freshness_state?: "current" | "lagged" | "unavailable" | "invalid";
  row_count?: number;
};
export type MarketCapitalSnapshot = {
  available: boolean;
  as_of?: string;
  window: "all";
  interpretations: string[];
  history_meta: {
    scope: "all_available";
    raw: true;
    start_date: string;
    end_date: string;
    points: number;
    source: string;
  };
  methodology?: {
    scope?: string;
    complete_day_threshold?: number;
    flow_warning?: string;
  };
  sources: Record<string, MarketSourceFreshness>;
  liquidity: {
    turnover_cny: number;
    top20_turnover_share?: number;
    top50_turnover_share?: number;
    note: string;
  };
  breadth: {
    advances: number;
    declines: number;
    flat: number;
    advance_ratio?: number;
    limit_up?: number;
    limit_down?: number;
    limit_source_available: boolean;
  };
  leverage: MarketSourceFreshness & {
    balance_cny?: number;
    purchases_cny?: number;
    repayments_cny?: number;
    daily_net_financing_cny?: number;
    five_day_net_financing_cny?: number;
    coverage_label?: string;
  };
  etf_flows: MarketSourceFreshness & {
    estimated_net_flow_cny?: number;
    groups?: Record<string, number>;
    fund_count?: number;
    flow_covered_funds?: number;
    coverage_ratio?: number;
    method?: string;
    note?: string;
  };
  funding_rates: MarketSourceFreshness & {
    overnight_pct?: number;
    seven_day_pct?: number;
    overnight_change_bp?: number;
    seven_day_change_bp?: number;
  };
  flow_proxy: MarketSourceFreshness & {
    provider?: string;
    method?: string;
    warning?: string;
    values?: Record<string, number | string | null>;
  };
  history: Array<{
    trade_date: string;
    stock_count: number;
    turnover_cny: number;
    advances: number;
    declines: number;
    flat: number;
  }>;
};
export type RawMarketSeries = {
  available: boolean;
  table: string;
  frequency: string;
  period_field?: string;
  start?: string;
  end?: string;
  points?: number;
  raw?: true;
  rows: Array<Record<string, string | number | null>>;
};
export type MacroMarketSnapshot = {
  available: boolean;
  series: Record<string, RawMarketSeries>;
  methodology: { raw: true; local_transforms: false; note: string };
};
export type FuturesProduct = {
  product_code: string;
  trade_date: string;
  mapping_ts_code: string;
  name?: string;
  fut_code?: string;
  exchange?: string;
  close?: number;
  settle?: number;
  vol?: number;
  amount?: number;
  oi?: number;
};
export type FuturesHistory = {
  available: boolean;
  product_code: string;
  history: Array<{
    trade_date: string;
    product_code: string;
    contract_code: string;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    settle?: number;
    vol?: number;
    amount?: number;
    oi?: number;
    oi_chg?: number;
  }>;
  history_meta: {
    scope: "all_available";
    raw: true;
    start_date?: string;
    end_date?: string;
    points: number;
    adjusted: false;
    source: string;
  };
};
export type FuturesCurve = {
  available: boolean;
  product_code: string;
  fut_code?: string;
  trade_date?: string;
  raw: true;
  items: Array<{
    trade_date: string;
    contract_code: string;
    name?: string;
    list_date?: string;
    delist_date?: string;
    close?: number;
    settle?: number;
    vol?: number;
    amount?: number;
    oi?: number;
  }>;
};
export type OptionSeries = {
  opt_code: string;
  exchange?: string;
  opt_type?: string;
  list_date?: string;
  latest_maturity?: string;
  contracts: number;
  active_contracts: number;
  underlying_code?: string;
  underlying_type?: "index" | "etf" | "futures_contract" | "unresolved";
};
export type OptionsSeriesResponse = {
  available: boolean;
  items: OptionSeries[];
  history_meta: {
    scope: "current_available";
    raw: true;
    start_date?: string;
    end_date?: string;
    backfill_target: string;
    source: string;
  };
};
export type OptionsHistory = {
  available: boolean;
  opt_code: string;
  history: Array<{
    trade_date: string;
    call_volume?: number;
    put_volume?: number;
    call_amount?: number;
    put_amount?: number;
    call_oi?: number;
    put_oi?: number;
    call_contracts?: number;
    put_contracts?: number;
  }>;
  history_meta: {
    scope: "current_available";
    raw_aggregation: true;
    start_date?: string;
    end_date?: string;
    points: number;
    source: string;
  };
};
export type OptionsChain = {
  available: boolean;
  opt_code: string;
  trade_date?: string;
  maturity?: string;
  total: number;
  limit: number;
  offset: number;
  raw: true;
  items: Array<{
    trade_date: string;
    ts_code: string;
    name?: string;
    exchange?: string;
    call_put?: "C" | "P";
    exercise_price?: number;
    maturity_date?: string;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    settle?: number;
    vol?: number;
    amount?: number;
    oi?: number;
  }>;
};
export type MarketUnderlying = {
  available: boolean;
  relationship:
    | "index"
    | "etf"
    | "futures_contract"
    | "deliverable_bond_basket"
    | "commodity_physical_market"
    | "unresolved";
  code?: string;
  name?: string;
  source?: string;
  series_available: boolean;
  methodology: string;
  specification?: Record<string, unknown>;
};
export type UnderlyingSeries = {
  available: boolean;
  relationship: string;
  code: string;
  source?: string;
  start?: string;
  end?: string;
  points?: number;
  raw?: true;
  rows: Array<{
    trade_date: string;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    pre_close?: number;
    vol?: number;
    amount?: number;
  }>;
};
export type MacroCatalog = {
  available: boolean;
  items: Array<{
    key: string;
    label: string;
    table: string | null;
    frequency?: string;
    period_field?: string;
    available: boolean;
    fields: string[];
    start?: string;
    end?: string;
    points?: number;
    source?: string;
    unavailable_reason?: string;
  }>;
  methodology: { raw?: true; local_transforms?: false; raw_history?: boolean; synthetic_prices?: boolean };
};
export type MacroSeriesDetail = {
  available: boolean;
  key: string;
  label: string;
  field: string;
  frequency: string;
  period_field: string;
  source: string;
  start?: string;
  end?: string;
  points: number;
  raw: true;
  rows: Array<{ period: string; value: number | null }>;
  recent_source_rows: Array<Record<string, string | number | null>>;
};
export type RatesCatalog = MacroCatalog;
export type RatesSeries = {
  available: boolean;
  key: string;
  label: string;
  field: string;
  frequency: string;
  period_field: string;
  source: string;
  start?: string;
  end?: string;
  points: number;
  raw: true;
  rows: Array<{
    period: string;
    value: number | null;
    bank?: string;
    repo_maturity?: string;
  }>;
};
export type RatesCurve = {
  available: boolean;
  key: string;
  date?: string;
  source?: string;
  raw?: true;
  unavailable_reason?: string;
  points: Array<{ tenor: string; value: number }>;
};
export type OptionSurface = {
  available: boolean;
  opt_code: string;
  trade_date?: string;
  source?: string;
  methodology?: Record<string, unknown>;
  items: Array<{
    ts_code: string;
    call_put?: string;
    exercise_price?: number;
    maturity_date?: string;
    implied_volatility?: number;
    delta?: number;
    gamma?: number;
    theta?: number;
    vega?: number;
    rho?: number;
    convergence_status: string;
    unavailable_reason?: string;
    model_family?: string;
    model_version?: string;
  }>;
};
export type OptionExposures = {
  available: boolean;
  opt_code: string;
  trade_date?: string;
  source?: string;
  methodology: string;
  items: Array<{
    maturity_date: string;
    call_put: string;
    gross_oi_delta?: number;
    gross_oi_gamma?: number;
    gross_oi_vega?: number;
    gross_open_interest?: number;
    resolved_contracts: number;
    contracts: number;
  }>;
};
export type Opportunity = {
  id: string;
  scope: "global" | "private";
  domain: "macro" | "rates" | "capital" | "futures" | "options" | "company" | "holder";
  subject_type: string;
  subject_key: string;
  playbook_key: string;
  title: string;
  state: "new" | "active" | "changed" | "challenged" | "invalidated" | "stale" | "closed";
  lifecycle_state: string;
  trigger: string;
  as_of?: string;
  hypothesis: string;
  affected_assets: string[];
  catalysts: string[];
  falsifiers: string[];
  source_dates: Record<string, string>;
  freshness: Record<string, { available?: boolean; as_of?: string; [key: string]: unknown }>;
  first_seen_at: string;
  last_seen_at: string;
  closed_at?: string;
  followed: boolean;
  follow?: { state: string; notes?: string } | null;
  evidence?: Array<{
    stance: "supporting" | "challenging" | "invalidating" | string;
    fact: string;
    source: string;
    source_date?: string;
    source_ref: Record<string, unknown>;
  }>;
  chart_refs?: Array<Record<string, unknown>>;
  snapshots?: Array<{
    id: string;
    state: string;
    as_of?: string;
    trigger: string;
    hypothesis: string;
    source_dates: Record<string, string>;
    freshness: Record<string, unknown>;
    evidence: Opportunity["evidence"];
    chart_refs: Array<Record<string, unknown>>;
    created_at: string;
  }>;
};
export type OpportunityFeed = {
  items: Opportunity[];
  groups: Record<string, Record<string, number>>;
  source_status: Record<string, { status: string; last_succeeded_at?: string; last_error?: string; duration_ms?: number }>;
  ordering: "domain_state_source_date";
  scoring: false;
  limit: number;
  offset: number;
};
export type RiskProfile = {
  account_equity?: number;
  currency: string;
  risk_per_trade: number;
  aggregate_open_risk: number;
  single_instrument_notional: number;
  derivative_premium_risk: number;
  max_leverage: number;
  sizing_method: "fixed_risk";
};
export type TradePlan = {
  id: string;
  opportunity_id: string;
  status: string;
  unavailable_reason?: string;
  direction?: string;
  instrument?: string;
  entry_trigger?: string;
  entry_price?: number;
  stop_price?: number;
  target_price?: number;
  horizon?: string;
  quantity?: number;
  max_loss?: number;
  notional?: number;
  checklist: string[];
  human_confirmation_required: true;
};
export type ContextSnapshot = {
  id: string;
  resource_type: string;
  resource_id: string;
  field?: string;
  visible_start?: string;
  visible_end?: string;
  source: string;
  methodology: string;
  created_at: string;
};
export type GlobalSearchResult = { type: string; id: string; title: string; subtitle?: string; href: string; navigation_only?: boolean };
export type PublicationDataset = { key: string; table?: string; frequency: string; actual_as_of?: string; expected_as_of?: string; history_start?: string; points: number; state: "current" | "delayed" | "missing" | "unavailable" | string; last_attempt_at?: string; last_success_at?: string; deferred_reason?: string; next_expected_update: string; unavailable_reason?: string };
export type PublicationStatus = { available: boolean; version: string; generated_at?: string; datasets: PublicationDataset[]; unavailable_reason?: string; read_only?: true; synthetic_substitution?: false };
export type DataStatus = { publication: PublicationStatus; opportunity_refresh: Array<{ domain: string; status: string; last_succeeded_at?: string; last_error?: string; duration_ms?: number; candidates_seen: number }>; read_only: true; request_time_refresh: false; scoring: false; methodology: string };
export type MarketCapability = { key: string; table?: string; domain: string; exposure: "typed_api" | "agent_query" | "internal" | "unavailable" | string; api: string[]; ui: string[]; physical: boolean; available: boolean; unavailable_reason?: string; publication_state?: string; updated_through?: string; coverage?: { ratio?: number; actual?: number; expected?: number; history_start?: string; points?: number } };
export type MarketCapabilities = { version: string; schema_version: number; source: string; generated_at?: string; publication_version?: string; physical_table_count?: number; available: boolean; read_only: true; synthetic_substitution: false; capabilities: MarketCapability[]; unavailable_reason?: string };
export type AllocationAccount = {
  id: string; name: string; base_currency: "CNY"; capital: number; horizon_months: number;
  liquidity_reserve: number; max_drawdown: number; max_leverage: number;
  future_cash_needs: Array<{ date: string; amount: number; note?: string }>;
  allowed_markets: string[]; allowed_instruments: string[]; hard_restrictions: string[];
  status: "active" | "archived"; current_policy_version_id?: string; created_at: string; updated_at: string;
};
export type AllocationSeriesStatus = {
  series_id?: string; sleeve_key: string; name: string; required: boolean; enabled?: boolean;
  quality_state: "unavailable" | "insufficient" | "stale" | "gapped" | "ready" | string;
  quality_reason?: string; first_month?: string; last_month?: string; observation_months?: number;
  unexplained_gap_months?: number; source_name?: string; return_type?: string; methodology?: string;
  currency_exposure?: Record<string, number>;
};
export type AllocationDataStatus = { available: boolean; formal_ready: boolean; minimum_months: number; series: AllocationSeriesStatus[]; missing_required: string[]; methodology: string };
export type AllocationSeriesHistory = { series_id: string; available: boolean; full_history: true; downsampled: false; methodology: string; points: Array<{ month_end: string; monthly_return?: number; cny_total_return_index: number; source_date: string; content_hash: string }> };
export type AllocationSleeve = { id: string; sleeve_key: string; label: string; target_weight: number; min_weight: number; max_weight: number; amount_cny: number; risk_contribution: number; currency_exposure: Record<string, number>; source_series_id?: string };
export type AllocationImplementation = { id: string; sleeve_key: string; instrument_type: string; instrument_code: string; instrument_name: string; target_weight: number; amount_cny: number; underlying_key: string; margin_cash?: number; premium_cash?: number; delta_equivalent?: number; gross_notional?: number; net_notional?: number; max_loss?: number; gamma?: number; vega?: number; metadata: Record<string, unknown> };
export type AllocationPolicyVersion = {
  id: string; account_id: string; version: number; feasibility_status: "feasible" | "infeasible" | "unavailable" | string;
  quality_status: string; content_hash: string; confirmed: boolean; created_at: string;
  account?: AllocationAccount; constraint_snapshot?: Record<string, unknown>; methodology_snapshot?: Record<string, unknown>;
  data_snapshot?: Record<string, unknown>; risk_summary?: Record<string, number>; stress_results?: Array<{ scenario: string; return: number }>;
  infeasible_reasons?: string[]; sleeves?: AllocationSleeve[]; implementations?: AllocationImplementation[];
};

export type WealthProfile = {
  id: string; name: string; base_currency: "CNY"; annual_essential_spending: number;
  short_bucket_months: number; medium_bucket_months: number; aspirational_cap: number;
  satellite_cap: number; settings_json: Record<string, unknown>;
};
export type HouseholdMember = {
  id: string; name: string; role: "self" | "partner" | "dependent" | "parent" | "other";
  birth_date: string; age: number; retirement_age?: number; dependency_end_date?: string;
  annual_income: number; income_type?: string; income_stability?: "stable" | "variable" | "uncertain";
  is_primary: boolean; notes?: string; life_stage: "accumulation" | "transition" | "retired" | "unspecified";
};
export type WealthAsset = {
  id: string; name: string; category: string; value_cny: number; original_currency?: string;
  original_value?: number; liquidity: "liquid" | "limited" | "illiquid"; allocatable: boolean;
  owner_member_id?: string; notes?: string;
};
export type WealthLiability = { id: string; name: string; category: string; balance_cny: number; monthly_payment_cny: number; due_date?: string; owner_member_id?: string; notes?: string };
export type WealthGoal = {
  id: string; name: string; member_id?: string; target_amount_cny: number; target_date: string;
  priority: "essential" | "important" | "aspirational"; flexibility: "fixed" | "flexible";
  prepared_amount_cny: number; funding_gap_cny: number; coverage_ratio: number; bucket: "short" | "medium" | "long"; notes?: string;
};
export type WealthAssignment = { id?: string; asset_id: string; goal_id?: string; layer?: "safety" | "market" | "aspirational"; amount_cny: number; notes?: string };
export type WealthSummary = {
  total_assets_cny: number; total_liabilities_cny: number; net_wealth_cny: number; liquid_wealth_cny: number;
  allocatable_wealth_cny: number; annual_household_income_cny: number; essential_spending_coverage_months?: number;
  safety_required_cny: number; market_available_cny: number; aspirational_limit_cny: number;
  core_budget_cny: number; satellite_budget_cny: number; layer_assignments_cny: Record<string, number>;
  goal_funding_gap_cny: number;
};
export type WealthAggregate = { profile: WealthProfile; members: HouseholdMember[]; assets: WealthAsset[]; liabilities: WealthLiability[]; goals: WealthGoal[]; assignments: WealthAssignment[]; framework: { summary: WealthSummary; conflicts: string[]; ready: boolean } };
export type WealthFrameworkVersion = { id: string; profile_id: string; version: number; snapshot: Record<string, unknown>; summary: WealthSummary; conflicts: string[]; content_hash: string; created_at: string };
export type SaaTarget = { key: string; label: string; layer: "safety" | "market" | "aspirational"; target_weight: number; min_weight: number; max_weight: number };
export type SaaPolicyVersion = { id: string; profile_id: string; framework_version_id: string; source_allocation_policy_version_id?: string; version: number; name: string; effective_date: string; review_date: string; targets: SaaTarget[]; constraints_snapshot: Record<string, unknown>; source_type: "manual" | "allocation_policy"; status: "draft" | "confirmed" | "superseded"; content_hash: string; created_at: string };
export type TaaOverlay = { id: string; profile_id: string; saa_version_id: string; opportunity_snapshot_id?: string; title: string; deltas: Record<string, number>; rationale: string; evidence: Array<Record<string, unknown>>; falsifiers: string[]; starts_at: string; review_at: string; expires_at: string; status: "draft" | "confirmed" | "closed" | "expired"; content_hash: string; created_at: string; updated_at: string };

const base = "/agent";
export const agentPlatformApi = {
  health: () => apiJson<{ status: string; mode: string }>(`${base}/health`),
  models: () =>
    apiJson<{ items: AgentModelProfile[] }>(`${base}/model-credentials`),
  createModel: (body: object) =>
    apiJson<AgentModelProfile>(`${base}/model-credentials`, {
      method: "POST",
      body,
    }),
  agents: () =>
    apiJson<{
      items: AgentDefinition[];
      builtin_tools: string[];
      mcp_tools: Array<{ name: string; server: string; description: string }>;
    }>(`${base}/definitions`),
  runs: () => apiJson<{ items: AgentRun[] }>(`${base}/runs`),
  runTrace: (id: string) => apiJson<AgentRunTrace>(`${base}/runs/${id}/trace`),
  createRun: (body: object) =>
    apiJson<AgentRun>(`${base}/runs`, { method: "POST", body }),
  sessions: (includeArchived = false) =>
    apiJson<{ items: AgentSession[] }>(
      `${base}/sessions?include_archived=${includeArchived}`,
    ),
  createSession: (body: {
    agent_definition_id: string;
    title?: string;
    interaction_mode?: InteractionMode;
    workspace_scope?: WorkspaceScope;
    company_code?: string | null;
  }) => apiJson<AgentSession>(`${base}/sessions`, { method: "POST", body }),
  updateSession: (
    id: string,
    body: {
      title?: string;
      is_pinned?: boolean;
      archived?: boolean;
      interaction_mode?: InteractionMode;
      workspace_scope?: WorkspaceScope;
      company_code?: string | null;
    },
  ) =>
    apiJson<AgentSession>(`${base}/sessions/${id}`, { method: "PATCH", body }),
  deleteSession: (id: string) =>
    apiJson<{ ok: boolean }>(`${base}/sessions/${id}`, { method: "DELETE" }),
  timeline: (id: string) =>
    apiJson<{
      session: AgentSession;
      messages: AgentMessage[];
      runs: AgentRun[];
    }>(`${base}/sessions/${id}/timeline`),
  sendMessage: (
    id: string,
    body: {
      content: string;
      client_request_id: string;
      agent_definition_id?: string;
      attachment_ids?: string[];
      context_snapshot_ids?: string[];
    },
  ) =>
    apiJson<{ run: AgentRun; session: AgentSession }>(
      `${base}/sessions/${id}/messages`,
      { method: "POST", body },
    ),
  createContextSnapshot: (body: {
    resource_type:
      | "macro"
      | "futures"
      | "options"
      | "underlying"
      | "capital"
      | "rates"
      | "opportunity"
      | "trade_plan"
      | "allocation_policy";
    resource_id: string;
    field?: string;
    visible_start?: string;
    visible_end?: string;
    selected_point?: Record<string, unknown>;
    source: string;
    methodology: string;
  }) =>
    apiJson<ContextSnapshot>(`${base}/context-snapshots`, {
      method: "POST",
      body,
    }),
  riskProfile: () => apiJson<RiskProfile>(`${base}/risk-profile`),
  updateRiskProfile: (body: Partial<RiskProfile>) =>
    apiJson<RiskProfile>(`${base}/risk-profile`, { method: "PUT", body }),
  allocationDataStatus: () => apiJson<AllocationDataStatus>(`${base}/allocation/data-status`),
  allocationUniverse: () => apiJson<{ catalog: AllocationDataStatus; instruments: AllocationImplementation[]; scoring: false }>(`${base}/allocation/universe`),
  allocationSeriesHistory: (seriesId: string) => apiJson<AllocationSeriesHistory>(`${base}/allocation/series/${encodeURIComponent(seriesId)}`),
  allocationAccounts: () => apiJson<{ items: AllocationAccount[] }>(`${base}/allocation-accounts`),
  createAllocationAccount: (body: Omit<AllocationAccount, "id" | "status" | "current_policy_version_id" | "created_at" | "updated_at">) =>
    apiJson<AllocationAccount>(`${base}/allocation-accounts`, { method: "POST", body }),
  updateAllocationAccount: (id: string, body: Partial<AllocationAccount>) =>
    apiJson<AllocationAccount>(`${base}/allocation-accounts/${id}`, { method: "PATCH", body }),
  deleteAllocationAccount: (id: string) => apiJson<{ ok: true }>(`${base}/allocation-accounts/${id}`, { method: "DELETE" }),
  allocationPolicyVersions: (accountId: string) => apiJson<{ items: AllocationPolicyVersion[]; current_policy_version_id?: string }>(`${base}/allocation-accounts/${accountId}/policy-versions`),
  allocationPolicyVersion: (id: string) => apiJson<AllocationPolicyVersion>(`${base}/allocation-policy-versions/${id}`),
  generateAllocationPolicy: (accountId: string) => apiJson<AllocationPolicyVersion>(`${base}/allocation-accounts/${accountId}/policy-versions`, { method: "POST" }),
  generateAllocationPolicyWithMethod: (accountId: string, body: { methodology_key: "black_litterman" | "core_satellite" | "risk_parity" | "all_weather" | "lifecycle"; view_snapshot?: Record<string, unknown> }) =>
    apiJson<AllocationPolicyVersion>(`${base}/allocation-accounts/${accountId}/policy-versions`, { method: "POST", body }),
  confirmAllocationPolicy: (accountId: string, versionId: string) => apiJson<AllocationPolicyVersion>(`${base}/allocation-accounts/${accountId}/policy-versions/${versionId}/confirm`, { method: "POST" }),
  publishAllocationPolicyAsSaa: (versionId: string, body: { framework_version_id: string; name: string; effective_date: string; review_date: string }) =>
    apiJson<SaaPolicyVersion>(`${base}/allocation-policy-versions/${versionId}/publish-saa`, { method: "POST", body }),
  wealthProfile: () => apiJson<WealthAggregate>(`${base}/wealth-profile`),
  updateWealthProfile: (body: Partial<WealthProfile>) => apiJson<WealthAggregate>(`${base}/wealth-profile`, { method: "PUT", body }),
  createWealthMember: (body: Omit<HouseholdMember, "id" | "age" | "life_stage">) => apiJson<HouseholdMember>(`${base}/wealth-profile/members`, { method: "POST", body }),
  updateWealthMember: (id: string, body: Omit<HouseholdMember, "id" | "age" | "life_stage">) => apiJson<HouseholdMember>(`${base}/wealth-profile/members/${id}`, { method: "PUT", body }),
  deleteWealthMember: (id: string) => apiJson<{ ok: true }>(`${base}/wealth-profile/members/${id}`, { method: "DELETE" }),
  createWealthAsset: (body: Omit<WealthAsset, "id">) => apiJson<WealthAsset>(`${base}/wealth-profile/assets`, { method: "POST", body }),
  updateWealthAsset: (id: string, body: Omit<WealthAsset, "id">) => apiJson<WealthAsset>(`${base}/wealth-profile/assets/${id}`, { method: "PUT", body }),
  deleteWealthAsset: (id: string) => apiJson<{ ok: true }>(`${base}/wealth-profile/assets/${id}`, { method: "DELETE" }),
  createWealthLiability: (body: Omit<WealthLiability, "id">) => apiJson<WealthLiability>(`${base}/wealth-profile/liabilities`, { method: "POST", body }),
  deleteWealthLiability: (id: string) => apiJson<{ ok: true }>(`${base}/wealth-profile/liabilities/${id}`, { method: "DELETE" }),
  createWealthGoal: (body: Omit<WealthGoal, "id" | "prepared_amount_cny" | "funding_gap_cny" | "coverage_ratio" | "bucket">) => apiJson<WealthGoal>(`${base}/wealth-profile/goals`, { method: "POST", body }),
  deleteWealthGoal: (id: string) => apiJson<{ ok: true }>(`${base}/wealth-profile/goals/${id}`, { method: "DELETE" }),
  replaceWealthAssignments: (body: WealthAssignment[]) => apiJson<WealthAggregate>(`${base}/wealth-profile/assignments`, { method: "PUT", body }),
  wealthFrameworkPreview: () => apiJson<{ preview: true; write_performed: false; summary: WealthSummary; conflicts: string[]; ready: boolean }>(`${base}/wealth-profile/framework-preview`, { method: "POST" }),
  wealthFrameworkVersions: () => apiJson<{ items: WealthFrameworkVersion[] }>(`${base}/wealth-profile/framework-versions`),
  createWealthFrameworkVersion: () => apiJson<WealthFrameworkVersion>(`${base}/wealth-profile/framework-versions`, { method: "POST" }),
  saaPolicyVersions: () => apiJson<{ items: SaaPolicyVersion[] }>(`${base}/saa-policy-versions`),
  createSaaPolicyVersion: (body: { framework_version_id: string; source_allocation_policy_version_id?: string; name: string; effective_date: string; review_date: string; targets: SaaTarget[] }) => apiJson<SaaPolicyVersion>(`${base}/saa-policy-versions`, { method: "POST", body }),
  confirmSaaPolicyVersion: (id: string) => apiJson<SaaPolicyVersion>(`${base}/saa-policy-versions/${id}/confirm`, { method: "POST" }),
  taaOverlays: () => apiJson<{ items: TaaOverlay[] }>(`${base}/taa-overlays`),
  createTaaOverlay: (body: { saa_version_id: string; opportunity_snapshot_id?: string; title: string; deltas: Record<string, number>; rationale: string; evidence?: Array<Record<string, unknown>>; falsifiers?: string[]; starts_at: string; review_at: string; expires_at: string }) => apiJson<TaaOverlay>(`${base}/taa-overlays`, { method: "POST", body }),
  confirmTaaOverlay: (id: string) => apiJson<TaaOverlay>(`${base}/taa-overlays/${id}/confirm`, { method: "POST" }),
  closeTaaOverlay: (id: string) => apiJson<TaaOverlay>(`${base}/taa-overlays/${id}/close`, { method: "POST" }),
  uploadAttachment: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiForm<{ id: string; fileName: string }>("/files/upload", form, {
      method: "POST",
    });
  },
  compactSession: (id: string) =>
    apiJson<AgentSession>(`${base}/sessions/${id}/compact`, { method: "POST" }),
  stopSession: (id: string) =>
    apiJson<AgentRun>(`${base}/sessions/${id}/stop`, { method: "POST" }),
  controlRun: (id: string, action: "pause" | "resume" | "cancel") =>
    apiJson<AgentRun>(`${base}/runs/${id}/${action}`, { method: "POST" }),
  approvals: () => apiJson<{ items: AgentApproval[] }>(`${base}/approvals`),
  resolveApproval: (
    id: string,
    decision: "approved" | "rejected",
    scope: "once" | "always" = "once",
  ) =>
    apiJson(`${base}/approvals/${id}/resolve`, {
      method: "POST",
      body: { decision, scope },
    }),
  memories: (includeDeleted = false) =>
    apiJson<{ items: AgentMemory[] }>(
      `${base}/memories?include_deleted=${includeDeleted}`,
    ),
  learningMemories: () =>
    apiJson<{ available: boolean; state: string; generated_at?: string; memory_count?: number; memories: GlobalLearningMemory[] }>(`${base}/learning/memories`),
  learningFeedback: (body: { message_id: string; feedback: "adopted" | "rejected" | "correction" | "preference"; comment?: string }) =>
    apiJson<{ accepted: boolean; event_id: string }>(`${base}/learning/feedback`, { method: "POST", body }),
  deleteMemory: (id: string) =>
    apiJson(`${base}/memories/${id}`, { method: "DELETE" }),
  restoreMemory: (id: string) =>
    apiJson(`${base}/memories/${id}/restore`, { method: "POST" }),
  mcpServers: () => apiJson<{ items: MCPServer[] }>(`${base}/mcp-servers`),
  createMcp: (body: object) =>
    apiJson<MCPServer>(`${base}/mcp-servers`, { method: "POST", body }),
  schedules: () => apiJson<{ items: AgentSchedule[] }>(`${base}/schedules`),
  createSchedule: (body: object) =>
    apiJson<AgentSchedule>(`${base}/schedules`, { method: "POST", body }),
  updateSchedule: (id: string, body: Partial<Pick<AgentSchedule, "name" | "prompt" | "cron" | "timezone" | "enabled">>) =>
    apiJson<AgentSchedule>(`${base}/schedules/${id}`, { method: "PATCH", body }),
  deleteSchedule: (id: string) => apiJson<{ ok: boolean }>(`${base}/schedules/${id}`, { method: "DELETE" }),
  usage: () => apiJson<Usage>(`${base}/usage`),
  globalSearch: (query: string) => apiJson<{ items: GlobalSearchResult[]; scoring: false }>(`${base}/search?q=${encodeURIComponent(query)}`),
  companies: (query: string) =>
    apiJson<{ items: CompanySearchItem[] }>(
      `${base}/companies?query=${encodeURIComponent(query)}`,
    ),
  watchlist: () => apiJson<{ items: WatchlistItem[] }>(`${base}/watchlist`),
  addWatchlist: (company: string) =>
    apiJson<WatchlistItem>(`${base}/watchlist`, {
      method: "POST",
      body: { company },
    }),
  removeWatchlist: (companyCode: string) =>
    apiJson(`${base}/watchlist/${encodeURIComponent(companyCode)}`, {
      method: "DELETE",
    }),
  dossier: (companyCode: string) =>
    apiJson<CompanyDossier>(
      `${base}/dossiers/${encodeURIComponent(companyCode)}`,
    ),
  refreshDossier: (companyCode: string) =>
    apiJson(`${base}/dossiers/${encodeURIComponent(companyCode)}/refresh`, {
      method: "POST",
    }),
  searchHolders: (query: string) =>
    apiJson<{ items: HolderSearchItem[]; source_available: boolean }>(
      `${base}/holders/search?query=${encodeURIComponent(query)}`,
    ),
  holderWatchlist: () =>
    apiJson<{ items: HolderWatchItem[] }>(`${base}/holder-watchlist`),
  addHolderWatch: (body: { holder_name: string; holder_type: string }) =>
    apiJson<HolderWatchItem>(`${base}/holder-watchlist`, {
      method: "POST",
      body,
    }),
  updateHolderWatch: (
    id: string,
    body: { aliases?: string[]; enabled?: boolean },
  ) =>
    apiJson<HolderWatchItem>(`${base}/holder-watchlist/${id}`, {
      method: "PATCH",
      body,
    }),
  removeHolderWatch: (id: string) =>
    apiJson<{ ok: boolean }>(`${base}/holder-watchlist/${id}`, {
      method: "DELETE",
    }),
  refreshHolderWatch: (id: string) =>
    apiJson<{ ok: boolean; status: string }>(
      `${base}/holder-watchlist/${id}/refresh`,
      { method: "POST" },
    ),
  holderPositions: (
    id: string,
    view: "latest" | "history",
    limit = 200,
    offset = 0,
    allHistory = false,
  ) =>
    apiJson<{
      items: Array<HolderPosition | HolderHistoryEvent>;
      total: number;
      source_available: boolean;
      source_as_of?: string;
      watch: HolderWatchItem;
    }>(
      `${base}/holders/${id}/positions?view=${view}&limit=${limit}&offset=${offset}&all_history=${allHistory}`,
    ),
  holderEvents: (unreadOnly = false) =>
    apiJson<{ items: HolderInboxEvent[]; unread: number }>(
      `${base}/holder-events?unread_only=${unreadOnly}`,
    ),
  readHolderEvents: (eventIds: string[] = []) =>
    apiJson<{ ok: boolean; updated: number }>(`${base}/holder-events/read`, {
      method: "POST",
      body: { event_ids: eventIds },
    }),
  marketCapital: () => apiJson<MarketCapitalSnapshot>(`${base}/market-capital`),
  macroMarket: () => apiJson<MacroMarketSnapshot>(`${base}/macro-market`),
  futuresProducts: () =>
    apiJson<{
      available: boolean;
      as_of?: string;
      items: FuturesProduct[];
      source: string;
      raw: true;
    }>(`${base}/futures/products`),
  futuresHistory: (productCode: string) =>
    apiJson<FuturesHistory>(
      `${base}/futures/${encodeURIComponent(productCode)}/history`,
    ),
  futuresCurve: (productCode: string, tradeDate?: string) =>
    apiJson<FuturesCurve>(
      `${base}/futures/${encodeURIComponent(productCode)}/curve${tradeDate ? `?trade_date=${encodeURIComponent(tradeDate)}` : ""}`,
    ),
  optionsSeries: () => apiJson<OptionsSeriesResponse>(`${base}/options/series`),
  optionsHistory: (optCode: string) =>
    apiJson<OptionsHistory>(
      `${base}/options/${encodeURIComponent(optCode)}/history`,
    ),
  optionsChain: (
    optCode: string,
    params: {
      tradeDate?: string;
      maturity?: string;
      limit?: number;
      offset?: number;
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.tradeDate) query.set("trade_date", params.tradeDate);
    if (params.maturity) query.set("maturity", params.maturity);
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    const suffix = query.size ? `?${query.toString()}` : "";
    return apiJson<OptionsChain>(
      `${base}/options/${encodeURIComponent(optCode)}/chain${suffix}`,
    );
  },
};

const marketsBase = "/markets";
export const marketsApi = {
  dataStatus: () => apiJson<DataStatus>(`${marketsBase}/data-status`),
  capabilities: () => apiJson<MarketCapabilities>(`${marketsBase}/capabilities`),
  capital: () => apiJson<MarketCapitalSnapshot>(`${marketsBase}/capital`),
  macroCatalog: () => apiJson<MacroCatalog>(`${marketsBase}/macro/series`),
  macroSeries: (key: string, field: string) =>
    apiJson<MacroSeriesDetail>(
      `${marketsBase}/macro/series/${encodeURIComponent(key)}?field=${encodeURIComponent(field)}`,
    ),
  futuresProducts: () =>
    apiJson<{
      available: boolean;
      as_of?: string;
      items: FuturesProduct[];
      source: string;
      raw: true;
    }>(`${marketsBase}/futures/products`),
  futuresHistory: (code: string) =>
    apiJson<FuturesHistory>(
      `${marketsBase}/futures/${encodeURIComponent(code)}/history`,
    ),
  futuresCurve: (code: string) =>
    apiJson<FuturesCurve>(
      `${marketsBase}/futures/${encodeURIComponent(code)}/curve`,
    ),
  futuresUnderlying: (code: string) =>
    apiJson<MarketUnderlying>(
      `${marketsBase}/futures/${encodeURIComponent(code)}/underlying`,
    ),
  optionsCatalog: () =>
    apiJson<OptionsSeriesResponse>(`${marketsBase}/options/underlyings`),
  optionsHistory: (code: string) =>
    apiJson<OptionsHistory>(
      `${marketsBase}/options/${encodeURIComponent(code)}/history`,
    ),
  optionsChain: (
    code: string,
    params: {
      tradeDate?: string;
      maturity?: string;
      limit?: number;
      offset?: number;
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.tradeDate) query.set("trade_date", params.tradeDate);
    if (params.maturity) query.set("maturity", params.maturity);
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    return apiJson<OptionsChain>(
      `${marketsBase}/options/${encodeURIComponent(code)}/chain${query.size ? `?${query}` : ""}`,
    );
  },
  optionUnderlying: (code: string) =>
    apiJson<MarketUnderlying>(
      `${marketsBase}/options/${encodeURIComponent(code)}/underlying`,
    ),
  optionSurface: (code: string) =>
    apiJson<OptionSurface>(
      `${marketsBase}/options/${encodeURIComponent(code)}/surface`,
    ),
  optionExposures: (code: string) =>
    apiJson<OptionExposures>(
      `${marketsBase}/options/${encodeURIComponent(code)}/exposures`,
    ),
  underlyingSeries: (relationship: string, code: string) =>
    apiJson<UnderlyingSeries>(
      `${marketsBase}/underlyings/${encodeURIComponent(relationship)}/${encodeURIComponent(code)}/series`,
    ),
  ratesCatalog: () => apiJson<RatesCatalog>(`${marketsBase}/rates/catalog`),
  ratesSeries: (
    key: string,
    field: string,
    params: { bank?: string; maturity?: string } = {},
  ) => {
    const q = new URLSearchParams({ field });
    if (params.bank) q.set("bank", params.bank);
    if (params.maturity) q.set("maturity", params.maturity);
    return apiJson<RatesSeries>(
      `${marketsBase}/rates/series/${encodeURIComponent(key)}?${q}`,
    );
  },
  ratesCurve: (key: string) =>
    apiJson<RatesCurve>(
      `${marketsBase}/rates/curve?key=${encodeURIComponent(key)}`,
    ),
  bondFutures: () =>
    apiJson<{
      available: boolean;
      items: FuturesProduct[];
      methodology: string;
    }>(`${marketsBase}/bonds/futures`),
  convertibles: () =>
    apiJson<{
      available: boolean;
      items: Array<Record<string, string | number | null>>;
      total: number;
      source: string;
    }>(`${marketsBase}/bonds/convertibles`),
  opportunities: (params: {
    scope?: "all" | "global" | "private";
    domain?: string;
    state?: string;
    followed?: boolean;
    limit?: number;
    offset?: number;
  } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") query.set(key, String(value));
    });
    return apiJson<OpportunityFeed>(`${marketsBase}/opportunities${query.size ? `?${query}` : ""}`);
  },
  opportunity: (id: string) =>
    apiJson<Opportunity>(`${marketsBase}/opportunities/${id}`),
  followOpportunity: (id: string, body: { state?: "following" | "watching" | "paused"; notes?: string }) =>
    apiJson<{ followed: true; state: string; notes?: string }>(`${marketsBase}/opportunities/${id}/follow`, {
      method: "POST",
      body,
    }),
  updateOpportunityFollow: (id: string, body: { state?: "following" | "watching" | "paused"; notes?: string }) =>
    apiJson<{ followed: true; state: string; notes?: string }>(`${marketsBase}/opportunities/${id}/follow`, {
      method: "PATCH",
      body,
    }),
  unfollowOpportunity: (id: string) =>
    apiJson<{ ok: true }>(`${marketsBase}/opportunities/${id}/follow`, { method: "DELETE" }),
  createTradePlan: (id: string, body: Record<string, unknown>) =>
    apiJson<TradePlan>(`${marketsBase}/opportunities/${id}/trade-plan`, {
      method: "POST",
      body,
    }),
};
