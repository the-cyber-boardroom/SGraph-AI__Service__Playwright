# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Chat__Backend
# The model-backend seam (one per LLM: Bedrock / Ollama / OpenRouter / in-memory).
# The engine speaks only NEUTRAL messages/tools/content; each backend adapts to its
# wire format. This is the plan-07 reconciliation: the agentic loop is neutral, the
# wire-shaping lives in the adapter. Subclass per backend.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Capabilities import Schema__Chat__Capabilities
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Turn__Result import Schema__Chat__Turn__Result
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Usage        import Schema__Chat__Usage


class Chat__Backend(Type_Safe):

    def id(self) -> str:                                                          # 'bedrock' | 'ollama' | 'openrouter' | 'in-memory'
        raise NotImplementedError

    def models(self) -> list:                                                     # [Schema__Chat__Model]
        return []

    def capabilities(self, model_id: str) -> Schema__Chat__Capabilities:
        return Schema__Chat__Capabilities()

    def cost(self, model_id: str, usage: Schema__Chat__Usage) -> float:           # USD for a usage; $0 for local backends
        return 0.0

    def stream_turn(self, model_id: str, messages, system: str = None, options: dict = None):
        raise NotImplementedError                                                 # yields ('delta', text) | ('usage', Schema__Chat__Usage)

    def converse(self, model_id: str, messages, system: str = None,
                 tools=None, options: dict = None) -> Schema__Chat__Turn__Result:
        raise NotImplementedError                                                 # tool-aware, non-streaming — the agentic loop's call
