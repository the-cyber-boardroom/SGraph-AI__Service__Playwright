#!/usr/bin/env bash
# ── local-llm-claude.sh ──────────────────────────────────────────────────────
# Container launcher. Points Claude Code at the LiteLLM sidecar, which
# translates the Anthropic Messages API to Ollama's /api/chat on the host.
set -euo pipefail

# Default base URL is the sidecar; no /v1 suffix (Anthropic SDK appends it).
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-http://litellm:4000}"
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

echo "[local-claude] ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL"
echo "[local-claude] ANTHROPIC_MODEL=$ANTHROPIC_MODEL"

# ── Pre-flight 1: LiteLLM sidecar health (warn-only) ─────────────────────────
LITELLM_HEALTH_URL="${ANTHROPIC_BASE_URL%/}/health/liveliness"
echo "[local-claude] probing LiteLLM at $LITELLM_HEALTH_URL ..."
if curl -sf --max-time 3 "$LITELLM_HEALTH_URL" >/dev/null 2>&1; then
  echo "[local-claude] LiteLLM sidecar is live."
else
  echo "[local-claude] WARNING: could not reach $LITELLM_HEALTH_URL"
  echo "[local-claude]   the sidecar may still be starting; Claude Code will retry."
fi

# ── Pre-flight 2: host Ollama catalogue (warn-only, independent of base URL) ─
OLLAMA_TAGS_URL="http://host.docker.internal:11434/api/tags"
echo "[local-claude] probing host Ollama at $OLLAMA_TAGS_URL ..."
if MODELS_JSON="$(curl -sf --max-time 3 "$OLLAMA_TAGS_URL" 2>/dev/null)"; then
  echo "[local-claude] host Ollama reachable; available models:"
  echo "$MODELS_JSON" | jq -r '.models[].name' 2>/dev/null | sed 's/^/  - /' \
    || echo "  (could not parse model list)"
else
  echo "[local-claude] WARNING: could not reach $OLLAMA_TAGS_URL"
  echo "[local-claude]   ensure 'ollama serve' is running on the host with"
  echo "[local-claude]   OLLAMA_HOST=0.0.0.0:11434 (launchctl setenv + restart Ollama.app)."
fi

exec claude "$@"
