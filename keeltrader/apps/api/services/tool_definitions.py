"""Tool schema definitions shared between REST API and MCP Server."""

TOOL_DEFINITIONS = [
    {
        "name": "get_positions",
        "description": "Query current positions across all exchanges",
        "parameters": {
            "type": "object",
            "properties": {
                "exchange": {"type": "string", "description": "Exchange name (okx/bybit), leave empty for all"},
                "symbol": {"type": "string", "description": "Trading pair (e.g. BTC/USDT), leave empty for all"},
            },
        },
    },
    {
        "name": "get_pnl",
        "description": "Query PnL for a specified period",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Period: today/week/month/all", "default": "today"},
            },
        },
    },
    {
        "name": "query_trades",
        "description": "Query historical trade records",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair filter"},
                "days": {"type": "integer", "description": "Number of days to query", "default": 7},
                "limit": {"type": "integer", "description": "Number of results to return", "default": 50},
            },
        },
    },
    {
        "name": "analyze_performance",
        "description": "Analyze trading performance (win rate, profit factor, streaks, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze", "default": 30},
                "symbol": {"type": "string", "description": "Filter by trading pair"},
            },
        },
    },
    {
        "name": "get_market_data",
        "description": "Get market data (candlesticks + real-time price)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair (e.g. BTC/USDT)"},
                "timeframe": {"type": "string", "description": "Candlestick timeframe", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of candlesticks", "default": 100},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "analyze_market",
        "description": "AI technical analysis (MA/RSI/volatility, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair"},
                "timeframe": {"type": "string", "description": "Analysis timeframe", "default": "4h"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "place_order",
        "description": "Place an order (requires user confirmation)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair"},
                "side": {"type": "string", "enum": ["buy", "sell"], "description": "Buy or sell"},
                "amount": {"type": "number", "description": "Quantity"},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
                "price": {"type": "number", "description": "Limit order price"},
                "stop_loss": {"type": "number", "description": "Stop loss price"},
                "take_profit": {"type": "number", "description": "Take profit price"},
                "exchange": {"type": "string", "description": "Exchange"},
                "confirmed": {"type": "boolean", "description": "Whether confirmed", "default": False},
            },
            "required": ["symbol", "side", "amount"],
        },
    },
    {
        "name": "cancel_order",
        "description": "Cancel an order",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID"},
                "symbol": {"type": "string", "description": "Trading pair"},
                "exchange": {"type": "string", "description": "Exchange"},
            },
            "required": ["order_id", "symbol"],
        },
    },
    {
        "name": "manage_journal",
        "description": "Manage trade journal (view/create/update)",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "get", "create"], "default": "list"},
                "journal_id": {"type": "string", "description": "Journal ID (required for get)"},
                "data": {"type": "object", "description": "Creation data"},
                "days": {"type": "integer", "default": 30},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "update_settings",
        "description": "Update risk parameters and push preferences",
        "parameters": {
            "type": "object",
            "properties": {
                "settings": {"type": "object", "description": "Settings key-value pairs to update"},
            },
            "required": ["settings"],
        },
    },
    {
        "name": "generate_chart",
        "description": "Generate chart data (candlestick + indicator overlay)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair"},
                "chart_type": {"type": "string", "default": "candlestick"},
                "timeframe": {"type": "string", "default": "1h"},
                "indicators": {"type": "array", "items": {"type": "string"}, "description": "Overlay indicators (e.g. ma20, rsi)"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "backtest_strategy",
        "description": "Backtest a trading strategy (MA crossover, RSI reversal, breakout)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair"},
                "strategy": {"type": "string", "description": "Strategy name: ma_crossover/rsi/breakout"},
                "params": {"type": "object", "description": "Strategy parameters"},
                "days": {"type": "integer", "default": 90},
                "timeframe": {"type": "string", "default": "1d"},
            },
            "required": ["symbol", "strategy"],
        },
    },
    {
        "name": "replay_my_trades",
        "description": "Trade replay what-if analysis",
        "parameters": {
            "type": "object",
            "properties": {
                "journal_id": {"type": "string", "description": "Journal ID to replay"},
                "days": {"type": "integer", "description": "Replay period in days", "default": 7},
                "what_if": {"type": "object", "description": "What-if scenario (exit_price/position_size)"},
            },
        },
    },
    # AgentOS tools
    {
        "name": "run_daily_brief",
        "description": "Generate an AgentOS daily investment brief from read-only data sources",
        "parameters": {
            "type": "object",
            "properties": {
                "watchlist": {"type": "array", "items": {"type": "string"}, "description": "Symbols to include"},
                "symbols": {"type": "array", "items": {"type": "string"}, "description": "Alias for watchlist"},
            },
        },
    },
    {
        "name": "deep_research",
        "description": "Run structured AgentOS deep research for a symbol",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "market": {"type": "string", "description": "Optional market label"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "record_investment_decision",
        "description": "Record a human-in-the-loop investment decision journal entry",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "action": {"type": "string"},
                "thesis": {"type": "string"},
                "confidence": {"type": "number"},
                "human_decision": {"type": "string", "default": "pending"},
                "human_reason": {"type": "string"},
                "falsifiers": {"type": "array", "items": {}},
                "risk_plan": {"type": "object"},
                "position_plan": {"type": "object"},
            },
            "required": ["symbol", "action", "thesis"],
        },
    },
    {
        "name": "run_weekly_review",
        "description": "Generate pending AgentOS weekly review lessons from decision logs",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "query_tushare_data",
        "description": "Query allowlisted synchronized Tushare PostgreSQL tables without using a Tushare token",
        "parameters": {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "filters": {"type": "object"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["table"],
        },
    },
    {
        "name": "query_research_reports",
        "description": "Search report-kb research reports for AgentOS research context",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
                "companies": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query"],
        },
    },
    {
        "name": "backtest_hypothesis",
        "description": "Run a guarded AgentOS v1 backtest and persist the result",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "strategy": {"type": "string", "default": "ma_crossover"},
                "params": {"type": "object"},
                "hypothesis_id": {"type": "string"},
            },
            "required": ["symbol"],
        },
    },
]
