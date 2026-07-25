#!/usr/bin/env bash
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-fretelli/KeelTrader}"
DESCRIPTION="Self-hosted investment Research OS with a focused Research Agent, market evidence, report search, allocation, and thesis validation."

ADD_TOPICS=(
  research-agent
  investment-research
  llm
  rag
  pgvector
  fundamental-analysis
  decision-journal
  human-in-the-loop
  financial-ai
  nextjs
  fastapi
)

REMOVE_TOPICS=(
  billions
  behavioral-finance
  coaching
  psychology
  stock-market
  trading
  trading-psychology
  backtesting
  multi-agent
  agentos
)

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI is not installed" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh is not authenticated. Run 'gh auth login' or set GH_TOKEN." >&2
  exit 1
fi

args=(repo edit "$REPO" --description "$DESCRIPTION")
for topic in "${ADD_TOPICS[@]}"; do
  args+=(--add-topic "$topic")
done
for topic in "${REMOVE_TOPICS[@]}"; do
  args+=(--remove-topic "$topic")
done

gh "${args[@]}"
echo "Synced GitHub About metadata for $REPO"
