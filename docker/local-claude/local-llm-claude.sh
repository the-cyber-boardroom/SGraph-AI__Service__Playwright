#!/usr/bin/env bash
# ── local-llm-claude.sh ──────────────────────────────────────────────────────
# Container launcher — mirrors Section__Claude_Code__Firstboot.py:70-93.
# Points Claude Code at the host's Ollama OpenAI-compat endpoint.
set -euo pipefail

# Allow shell override; default to Docker Desktop's host gateway.
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-http://host.docker.internal:11434/v1}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-dummy}"
export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-dummy}"

# Single model name routed to every Claude tier (Opus/Sonnet/Haiku/SmallFast).
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"
export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-$OLLAMA_MODEL}"
export ANTHROPIC_DEFAULT_OPUS_MODEL="${ANTHROPIC_DEFAULT_OPUS_MODEL:-$OLLAMA_MODEL}"
export ANTHROPIC_DEFAULT_SONNET_MODEL="${ANTHROPIC_DEFAULT_SONNET_MODEL:-$OLLAMA_MODEL}"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="${ANTHROPIC_DEFAULT_HAIKU_MODEL:-$OLLAMA_MODEL}"
export ANTHROPIC_SMALL_FAST_MODEL="${ANTHROPIC_SMALL_FAST_MODEL:-$OLLAMA_MODEL}"

export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export DISABLE_AUTOUPDATER=1
export CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL=1
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=1024

# ── Pre-flight: list models on the host Ollama (warn-only) ───────────────────
# ANTHROPIC_BASE_URL is .../v1 — Ollama's native catalogue is at /api/tags.
TAGS_URL="${ANTHROPIC_BASE_URL%/v1}/api/tags"
echo "[local-claude] ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL"
echo "[local-claude] ANTHROPIC_MODEL=$ANTHROPIC_MODEL"
echo "[local-claude] probing host Ollama at $TAGS_URL ..."
if MODELS_JSON="$(curl -sf --max-time 3 "$TAGS_URL" 2>/dev/null)"; then
  echo "[local-claude] host Ollama reachable; available models:"
  echo "$MODELS_JSON" | jq -r '.models[].name' 2>/dev/null | sed 's/^/  - /' \
    || echo "  (could not parse model list)"
else
  echo "[local-claude] WARNING: could not reach $TAGS_URL"
  echo "[local-claude]   ensure 'ollama serve' is running on the host with"
  echo "[local-claude]   OLLAMA_HOST=0.0.0.0:11434 (or export ANTHROPIC_BASE_URL)."
fi

exec claude "$@"
