# Compatibility and support matrix

KeelTrader supports the following baseline for the current `v2` line:

| Component | Supported baseline | Notes |
|---|---|---|
| Docker Engine | 24+ | Docker Compose v2 required |
| Docker Compose | 2.24+ | `docker compose`, not legacy `docker-compose` |
| Python | 3.11 | API image and formatting target |
| Node.js | 20 LTS | Web build and local development |
| PostgreSQL | 15 + pgvector | Default self-host image uses pgvector on PostgreSQL 15 |
| Redis | 7.2 | Cache, rate limits, worker heartbeats |
| Browsers | Current and previous major Chrome/Edge/Firefox/Safari | JavaScript and secure cookies required |
| LLM APIs | OpenAI-compatible and Anthropic-compatible BYOK | Provider-specific capabilities may differ |

Only the latest tagged release and the current `v2` branch receive fixes. Database migrations are forward-only and additive within a minor release line. Before upgrading, back up PostgreSQL and record the currently deployed image digests.

Public images are built for Linux/amd64. Additional architectures are accepted when CI coverage and maintainer capacity permit.
