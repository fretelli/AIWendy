# KeelTrader — AI Native Trading Assistant

## Description

KeelTrader 是一个 AI 原生交易助手，支持加密货币（OKX/Bybit/Coinbase/Kraken）和美股/期货（IBKR）。通过自然语言对话管理持仓、执行交易、分析表现、检测行为模式、回测策略。

## MCP Server

- **SSE Endpoint**: `https://keeltrader.joyeeassets.com/mcp/sse`
- **Transport**: SSE (Server-Sent Events)

## Tools

### 查询类
- `get_positions` — 查询当前持仓（支持指定交易所）
- `get_pnl` — 查询盈亏（支持日/周/月/自定义周期）
- `query_trades` — 查询历史交易记录（按标的/时间段/方向筛选）
- `get_market_data` — 获取实时行情数据（价格/K线/指标）

### 交易执行
- `place_order` — 下单（需用户确认，内置风控检查）
- `cancel_order` — 撤销挂单

### 分析类
- `analyze_performance` — 分析交易表现（胜率、盈亏比、最大回撤、连续胜负）
- `detect_patterns` — 检测行为模式（FOMO、报复交易、过度交易等）
- `analyze_market` — AI 分析市场技术面（均线/RSI/波动率/趋势判断）

### 回测类
- `backtest_strategy` — 对话式回测（MA交叉/RSI反转/突破策略）
- `replay_my_trades` — 交易回放 what-if 分析

### 工具类
- `search_knowledge` — 搜索交易知识库（RAG）
- `manage_journal` — 管理交易日记
- `update_settings` — 更新风控参数和策略设置
- `generate_chart` — 生成图表数据

## Example Prompts

- "查持仓"
- "今日盈亏"
- "买 0.1 BTC"
- "分析我最近一个月的交易表现"
- "回测 BTC 20日均线突破策略，最近3个月"
- "如果我上周那笔 ETH 没有提前止损会怎样"
- "BTC 现在什么趋势"

## Authentication

MCP 连接默认使用 guest 用户。如需绑定个人交易所账户，请先在 Web UI (https://keeltrader.joyeeassets.com) 的设置页面添加交易所 API Key。
