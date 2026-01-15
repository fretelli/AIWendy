// Journal types for frontend

export enum TradeDirection {
  LONG = 'long',
  SHORT = 'short'
}

export enum TradeResult {
  WIN = 'win',
  LOSS = 'loss',
  BREAKEVEN = 'breakeven',
  OPEN = 'open'
}

export enum RuleViolationType {
  EARLY_EXIT = 'early_exit',
  LATE_EXIT = 'late_exit',
  NO_STOP_LOSS = 'no_stop_loss',
  OVER_LEVERAGE = 'over_leverage',
  REVENGE_TRADE = 'revenge_trade',
  FOMO = 'fomo',
  POSITION_SIZE = 'position_size',
  OTHER = 'other'
}

export interface JournalBase {
  project_id?: string;

  // Trade information
  symbol: string;
  market?: string;
  direction: TradeDirection;
  trade_date?: string;

  // Entry
  entry_time?: string;
  entry_price?: number;
  position_size?: number;

  // Exit
  exit_time?: string;
  exit_price?: number;

  // Results
  result: TradeResult;
  pnl_amount?: number;
  pnl_percentage?: number;

  // Risk management
  stop_loss?: number;
  take_profit?: number;
  risk_reward_ratio?: number;

  // Emotions (1-5 scale)
  emotion_before?: number;
  emotion_during?: number;
  emotion_after?: number;

  // Psychology
  confidence_level?: number;
  stress_level?: number;
  followed_rules: boolean;
  rule_violations: RuleViolationType[];

  // Notes
  setup_description?: string;
  exit_reason?: string;
  lessons_learned?: string;
  notes?: string;

  // Tags and strategy
  tags: string[];
  strategy_name?: string;

  // Attachments
  screenshots: string[];
}

export interface JournalCreate extends JournalBase {}

export interface JournalUpdate extends Partial<JournalBase> {}

export interface JournalResponse extends JournalBase {
  id: string;
  user_id: string;
  ai_insights?: string;
  detected_patterns?: string[];
  created_at: string;
  updated_at: string;
  is_winner: boolean;
  is_rule_violation: boolean;
}

export interface JournalListResponse {
  items: JournalResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface JournalStatistics {
  // Trade counts
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  breakeven_trades: number;
  open_trades: number;

  // Financial metrics
  total_pnl: number;
  average_win: number;
  average_loss: number;
  best_trade: number;
  worst_trade: number;

  // Performance ratios
  win_rate: number;
  profit_factor: number;

  // Psychology metrics
  average_confidence: number;
  average_stress: number;
  rule_violation_rate: number;

  // Streaks
  current_streak: number;
  best_streak: number;
  worst_streak: number;
}

export interface JournalFilter {
  project_id?: string;
  symbol?: string;
  market?: string;
  direction?: TradeDirection;
  result?: TradeResult;
  date_from?: string;
  date_to?: string;
  tags?: string[];
  followed_rules?: boolean;
}

export interface QuickJournalEntry {
  symbol: string;
  direction: TradeDirection;
  result: TradeResult;
  pnl_amount?: number;
  emotion_after: number;
  violated_rules: boolean;
  quick_note?: string;
}

export interface JournalImportPreviewResponse {
  columns: string[];
  sample_rows: Record<string, string>[];
  suggested_mapping: Record<string, string | null>;
  warnings: string[];
}

export interface JournalImportResponse {
  created: number;
  skipped: number;
  errors: string[];
}
