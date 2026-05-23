# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Chat__Backend__In_Memory
# A real, scripted backend for tests — NOT a mock. stream_turn pops scripted text;
# converse pops scripted Schema__Chat__Turn__Result objects (script a tool_use→end_turn
# sequence to exercise the agentic loop). Records every call. No network, runs on 3.11.
# Cost is a small fixed per-token price so the engine's cost-summing is exercised.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.chat.backend.Chat__Backend            import Chat__Backend
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Capabilities import Schema__Chat__Capabilities
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Content      import Schema__Chat__Content
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Turn__Result import Schema__Chat__Turn__Result
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Usage        import Schema__Chat__Usage

_PRICE_PER_TOKEN = 0.000001                                                       # notional, so cost-summing is exercised in tests


class Chat__Backend__In_Memory(Chat__Backend):
    scripted_stream : list                                                        # queue of (text, in, out, ms)
    scripted_turns  : list                                                        # queue of Schema__Chat__Turn__Result
    stream_calls    : list                                                        # recorded (model_id, messages, system)
    turn_calls      : list                                                        # recorded (model_id, messages, system, tools)

    def id(self) -> str:
        return 'in-memory'

    def capabilities(self, model_id: str) -> Schema__Chat__Capabilities:
        return Schema__Chat__Capabilities(streaming=True, tools=True, documents=True)

    def cost(self, model_id: str, usage: Schema__Chat__Usage) -> float:
        return (usage.input_tokens + usage.output_tokens) * _PRICE_PER_TOKEN

    def stream_turn(self, model_id: str, messages, system: str = None, options: dict = None):
        self.stream_calls.append((model_id, messages, system))
        text, in_tok, out_tok, latency = self.scripted_stream.pop(0) if self.scripted_stream else ('(no scripted reply)', 10, 5, 1)
        for word in text.split(' '):
            yield ('delta', word + ' ')
        yield ('usage', Schema__Chat__Usage(input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency))

    def converse(self, model_id: str, messages, system: str = None,
                 tools=None, options: dict = None) -> Schema__Chat__Turn__Result:
        self.turn_calls.append((model_id, list(messages), system, tools))
        if self.scripted_turns:
            return self.scripted_turns.pop(0)
        result = Schema__Chat__Turn__Result(stop_reason='end_turn', usage=Schema__Chat__Usage(input_tokens=5, output_tokens=5, latency_ms=1))
        result.content.append(Schema__Chat__Content(text='(no scripted turn)'))
        return result
