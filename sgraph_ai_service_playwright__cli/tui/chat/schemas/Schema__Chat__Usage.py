# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Usage (neutral)
# Normalised token usage; backends fill it from their own fields (Bedrock metadata /
# Ollama eval counts / OpenRouter usage). estimated=True when a backend omits tokens.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Usage(Type_Safe):
    input_tokens  : int   = 0
    output_tokens : int   = 0
    latency_ms    : int   = 0
    estimated     : bool  = False
