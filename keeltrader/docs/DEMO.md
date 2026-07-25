# Product walkthrough

KeelTrader is organized around one visible research assistant. Internally, a research run may invoke specialized roles such as fundamental analysis, macro context, red-team falsification, and review; users do not have to manage a collection of unrelated bots.

## Five-minute walkthrough

1. Start the self-hosted stack and open `http://localhost:3000`.
2. Create an account and add an OpenAI-compatible or Anthropic-compatible BYOK profile in `/agent`.
3. Start a research session and ask for a source-dated memo with explicit falsifiers.
4. Add a public HTTPS MCP server only if needed, inspect the discovered tools, and approve tools individually.
5. Bring a market or opportunity snapshot into the session explicitly; market data is not silently inserted into model context.
6. Record the decision, assumptions, review date, and invalidation conditions.
7. Use weekly review to propose lessons, then approve or reject each lesson before it can be reused.

## Trust boundaries to observe

- KeelTrader never places or cancels orders.
- BYOK and MCP tokens are encrypted at rest and excluded from logs and memory.
- Scheduled research uses only permanently approved tools.
- Research Cloud is disabled by default and requires both administrator enablement and per-user authorization.
- AI output remains a research artifact, not investment advice.

For the component and data flow diagram, see [ARCHITECTURE.md](ARCHITECTURE.md).
