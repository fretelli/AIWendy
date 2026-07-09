"""Tool schema definitions shared between REST API and MCP Server."""

TOOL_DEFINITIONS = [
    {
        "name": "run_daily_brief",
        "description": "Generate an AgentOS fundamental investment brief from read-only data sources",
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
        "description": "Run structured fundamental AgentOS research for a symbol",
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
        "description": "Search report-kb research reports for AgentOS fundamental research context",
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
        "name": "record_fundamental_validation",
        "description": "Record a fundamental thesis validation result without chart-based simulation",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "hypothesis_id": {"type": "string"},
                "conclusion": {"type": "string", "description": "observe/supported/rejected/revise"},
                "evidence": {"type": "array", "items": {}},
                "risks": {"type": "array", "items": {}},
                "notes": {"type": "string"},
            },
            "required": ["symbol"],
        },
    },
]
