# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Stream__Adapter
# Translates Bedrock converse_stream SSE events to NDJSON lines for --json mode.
# Each yielded string is one complete JSON line (no trailing newline).
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe


class Bedrock__Stream__Adapter(Type_Safe):

    def to_ndjson(self, stream_events):                                          # Generator — yields one NDJSON string per text-delta event
        for event in stream_events:
            delta = self.extract_delta(event)
            if delta is not None:
                yield json.dumps({'type': 'delta', 'text': delta})
        yield json.dumps({'type': 'done'})

    def extract_delta(self, event: dict):                                        # Returns the text delta from a contentBlockDelta event; None otherwise
        delta_block = event.get('contentBlockDelta')
        if delta_block:
            delta = delta_block.get('delta', {})
            return delta.get('text')
        return None

    def collect(self, stream_events) -> str:                                     # Collect all stream events into a single string (non-streaming fallback)
        parts = []
        for event in stream_events:
            delta = self.extract_delta(event)
            if delta:
                parts.append(delta)
        return ''.join(parts)

    def extract_usage(self, event: dict):                                        # Returns (input_tokens, output_tokens, latency_ms) from the trailing metadata event; None otherwise
        meta = event.get('metadata')
        if meta:
            usage   = meta.get('usage', {})
            metrics = meta.get('metrics', {})
            return (int(usage.get('inputTokens', 0)),
                    int(usage.get('outputTokens', 0)),
                    int(metrics.get('latencyMs', 0)))
        return None

    def collect_with_usage(self, stream_events) -> tuple:                        # → (text, input_tokens, output_tokens, latency_ms) — keeps the token count streaming throws away
        parts = []
        usage = (0, 0, 0)
        for event in stream_events:
            delta = self.extract_delta(event)
            if delta:
                parts.append(delta)
            found = self.extract_usage(event)
            if found is not None:
                usage = found
        return (''.join(parts), usage[0], usage[1], usage[2])
