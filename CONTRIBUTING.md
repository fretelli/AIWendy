# Contributing

Thanks for your interest in contributing to AIWendy!

## Quick start (recommended)

The easiest way to run the full stack locally is Docker Compose:

1. `cd aiwendy`
2. Copy env file: `Copy-Item .env.example .env` (PowerShell) or `cp .env.example .env`
3. Start: `docker compose up -d --build`

More details: `aiwendy/docs/SELF_HOSTING.md`

## Development (split mode)

You can also run DB/Redis in Docker and run the API/Web on your host:

- API: `aiwendy/docs/DEPLOYMENT.md`
- Web: `aiwendy/apps/web/package.json` scripts: `npm run dev`, `npm run lint`, `npm run type-check`

## Pull requests

- Keep PRs focused (one topic per PR).
- Include screenshots/GIFs for UI changes.
- Prefer adding/adjusting docs if behavior changes.
- Ensure CI passes (lint/type-check/compile checks).

## Reporting bugs / requesting features

Please use GitHub Issues and include:

- What you expected vs what happened
- Steps to reproduce
- Logs (redact secrets)
- OS / Node / Python versions

## Security

If you believe you found a security issue, please follow `SECURITY.md` instead of opening a public issue.
