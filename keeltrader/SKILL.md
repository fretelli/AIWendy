# KeelTrader — Investment Research AgentOS

## Description

KeelTrader is a self-evolving fundamental investment research AgentOS. It supports human-in-the-loop research briefs, report-KB search, structured decision journals, and weekly reviews.

KeelTrader is a research assistant and decision-discipline engine. It is not an automatic trading system, and generated analysis is not investment advice.

## MCP Server

- **SSE Endpoint**: `https://keeltrader.joyeeassets.com/mcp/sse`
- **Transport**: SSE (Server-Sent Events)

## Primary Capabilities

- Daily investment briefs for watchlists and symbols
- Deep research memos for individual securities or markets
- Report-KB semantic search over connected research reports
- Decision journal creation and outcome tracking
- Weekly review lessons with explicit approval before reuse
- Source-dated evidence retrieval and falsifier-oriented research analysis
- Tushare database reads without requiring an in-app Tushare token

## Example Prompts

- "Generate a daily brief for AAPL, NVDA, and QQQ"
- "Search research reports about AI capex and cloud margins"
- "Create a research memo for 300750.SZ"
- "Record this investment decision and the assumptions behind it"
- "Run a weekly review of my recent decisions"
- "Identify the strongest falsifiers for the current 300750.SZ research case"

## Authentication

Production deployments require authentication by default. Keep final trading decisions human-reviewed and do not treat model output as financial advice.
