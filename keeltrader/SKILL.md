# KeelTrader — AI Native Trading Assistant

## Description

KeelTrader is an AI-native trading assistant supporting crypto (OKX/Bybit/Coinbase/Kraken) and stocks/futures (IBKR). Manage positions, execute trades, analyze performance, detect behavior patterns, and backtest strategies via natural language.

## MCP Server

- **SSE Endpoint**: `https://keeltrader.joyeeassets.com/mcp/sse`
- **Transport**: SSE (Server-Sent Events)

## Tools

### Queries
- `get_positions` — Query current positions (supports filtering by exchange)
- `get_pnl` — Query PnL (day/week/month/custom period)
- `query_trades` — Query historical trades (filter by symbol/period/direction)
- `get_market_data` — Get real-time market data (price/candlesticks/indicators)

### Trade Execution
- `place_order` — Place order (requires confirmation, built-in risk checks)
- `cancel_order` — Cancel a pending order

### Analysis
- `analyze_performance` — Analyze trading performance (win rate, profit factor, max drawdown, streaks)
- `detect_patterns` — Detect behavior patterns (FOMO, revenge trading, overtrading, etc.)
- `analyze_market` — AI technical analysis (MA/RSI/volatility/trend)

### Backtesting
- `backtest_strategy` — Backtest strategies (MA crossover/RSI reversal/breakout)
- `replay_my_trades` — Trade replay what-if analysis

### Utilities
- `search_knowledge` — Search trading knowledge base (RAG)
- `manage_journal` — Manage trade journal
- `update_settings` — Update risk parameters and strategy settings
- `generate_chart` — Generate chart data

## Example Prompts

- "Show my positions"
- "Today's PnL"
- "Buy 0.1 BTC"
- "Analyze my trading performance for the past month"
- "Backtest BTC 20-day MA crossover strategy, last 3 months"
- "What if I hadn't cut my ETH loss early last week"
- "What's the trend on BTC right now"

## Authentication

MCP connections use a guest user by default. To link your exchange account, add your exchange API keys in the Settings page at https://keeltrader.joyeeassets.com.
