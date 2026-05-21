# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__AWS_Source
# Live Bedrock chat source. Wraps the existing Runtime client (the sole boto3
# boundary) + Stream adapter: streams a multi-turn converse and yields delta chunks
# as they arrive, then the usage tuple from the terminal metadata event. This is the
# ONLY chat-tui file that pulls boto3 — the engine and tests never import it.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Runtime__AWS__Client import Bedrock__Runtime__AWS__Client
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Stream__Adapter      import Bedrock__Stream__Adapter
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__Source      import Bedrock__Chat__Source


class Bedrock__Chat__AWS_Source(Bedrock__Chat__Source):
    runtime : Bedrock__Runtime__AWS__Client
    adapter : Bedrock__Stream__Adapter

    def stream_turn(self, model_id: str, messages: list, region: str = '', system: str = None):
        events = self.runtime.converse_stream_messages(model_id, messages, region=region or None, system=system)
        for event in events:
            delta = self.adapter.extract_delta(event)
            if delta is not None:
                yield ('delta', delta)
            usage = self.adapter.extract_usage(event)
            if usage is not None:
                yield ('usage', usage)

    def converse_turn(self, model_id: str, messages: list, region: str = '', system: str = None,
                      tool_config: dict = None) -> dict:
        response = self.runtime.converse_messages(model_id, messages, region=region or None,
                                                 system=system, tool_config=tool_config)
        message = response.get('output', {}).get('message', {})
        usage   = response.get('usage', {})
        metrics = response.get('metrics', {})
        return {'stop_reason'  : response.get('stopReason', 'end_turn'),
                'content'      : message.get('content', []),
                'input_tokens' : int(usage.get('inputTokens', 0)),
                'output_tokens': int(usage.get('outputTokens', 0)),
                'latency_ms'   : int(metrics.get('latencyMs', 0))}
