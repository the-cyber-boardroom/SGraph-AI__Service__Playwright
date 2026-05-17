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
