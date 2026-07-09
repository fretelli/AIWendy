#!/usr/bin/env bash
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-fretelli/KeelTrader}"
DESCRIPTION="Self-evolving investment research AgentOS with human-in-the-loop decision journals, report-KB search, multi-agent analysis, and backtesting workflows."

ADD_TOPICS=(
  agentos
  investment-research
  multi-agent
  llm
  rag
  pgvector
  backtesting
  decision-journal
  human-in-the-loop
  financial-ai
  nextjs
  fastapi
)

REMOVE_TOPICS=(
  billions
  coaching
  psychology
  trading-psychology
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
