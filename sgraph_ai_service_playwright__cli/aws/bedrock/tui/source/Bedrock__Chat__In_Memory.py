# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__In_Memory
# A real, scripted chat source for tests — NOT a mock. Each call to stream_turn pops
# the next scripted reply (text + exact token counts + latency), yields the text as a
# few deltas, then the usage tuple. It records every call so tests can assert that the
# engine passed the right model and full history. No boto3, runs on 3.11.
#
# scripted item shape: (reply_text, input_tokens, output_tokens, latency_ms)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__Source import Bedrock__Chat__Source


class Bedrock__Chat__In_Memory(Bedrock__Chat__Source):
    scripted       : list                                                         # streaming queue of (text, in, out, ms)
    scripted_turns : list                                                         # agentic queue of converse_turn dicts
    calls          : list                                                         # recorded streaming (model_id, messages, system)
    turn_calls     : list                                                         # recorded agentic (model_id, messages, system, tool_config)

    def stream_turn(self, model_id: str, messages: list, region: str = '', system: str = None):
        self.calls.append((model_id, messages, system))
        if self.scripted:
            text, in_tok, out_tok, latency = self.scripted.pop(0)
        else:
            text, in_tok, out_tok, latency = ('(no scripted reply)', 10, 5, 1)    # deterministic fallback
        for word in text.split(' '):                                              # stream word-by-word to exercise the delta path
            yield ('delta', word + ' ')
        yield ('usage', (in_tok, out_tok, latency))

    def converse_turn(self, model_id: str, messages: list, region: str = '', system: str = None,
                      tool_config: dict = None) -> dict:
        self.turn_calls.append((model_id, list(messages), system, tool_config))
        if self.scripted_turns:
            return dict(self.scripted_turns.pop(0))
        return {'stop_reason'  : 'end_turn',                                       # deterministic fallback
                'content'      : [{'text': '(no scripted turn)'}],
                'input_tokens' : 5, 'output_tokens': 5, 'latency_ms': 1}
