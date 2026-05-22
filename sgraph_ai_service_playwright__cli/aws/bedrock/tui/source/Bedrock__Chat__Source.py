# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Source
# The seam the chat engine streams a turn through. Implementations yield 2-tuples:
#   ('delta', text)            one incremental token chunk
#   ('usage', (in, out, ms))   the terminal usage from the metadata event
# Two implementations: AWS (live Bedrock) and In_Memory (scripted, for tests — no
# mocks, no boto3). This module imports neither, so the engine + tests stay boto3-free.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe


class Bedrock__Chat__Source(Type_Safe):

    def stream_turn(self, model_id: str, messages: list, region: str = '', system: str = None):
        raise NotImplementedError                                                 # yields ('delta', text) | ('usage', (in, out, ms))

    def converse_turn(self, model_id: str, messages: list, region: str = '', system: str = None,
                      tool_config: dict = None) -> dict:                           # non-streaming, tool-aware (the agentic loop)
        raise NotImplementedError                                                 # → {stop_reason, content[], input_tokens, output_tokens, latency_ms}
