# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Observe__Agent__Tracer
# 5 tests exercising cross-source trace queries via stub adapters.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.observe.Source__Registry              import Source__Registry
from sgraph_ai_service_playwright__cli.aws.observe.service.Observe__Agent__Tracer import Observe__Agent__Tracer
from tests.unit.sgraph_ai_service_playwright__cli.aws.observe._Stub__Source__Adapter import _Stub__Source__Adapter


SESSION_ID = 'sess-abc-123'


def _make_registry_with_events() -> Source__Registry:
    reg     = Source__Registry()
    adapter = _Stub__Source__Adapter()
    adapter.add_stream('my-stream')
    adapter.add_event('2026-05-17T10:00:00Z', f'start session {SESSION_ID}',  stream='my-stream')
    adapter.add_event('2026-05-17T10:01:00Z', f'end   session {SESSION_ID}',  stream='my-stream')
    adapter.add_event('2026-05-17T10:02:00Z', 'unrelated event',              stream='my-stream')
    reg.register('stub', adapter)
    return reg


class Test__Observe__Agent__Tracer:

    def setup_method(self):
        self.registry = _make_registry_with_events()
        self.tracer   = Observe__Agent__Tracer(registry=self.registry)

    def test_1__trace_returns_list(self):
        result = self.tracer.trace(SESSION_ID)
        assert isinstance(result, list)

    def test_2__trace_finds_matching_events(self):
        result = self.tracer.trace(SESSION_ID)
        assert len(result) >= 2                                         # at least the two session events

    def test_3__trace_summary_has_required_keys(self):
        summary = self.tracer.trace_summary(SESSION_ID)
        assert 'session_id'    in summary
        assert 'total_events'  in summary
        assert 'by_source'     in summary
        assert 'events'        in summary

    def test_4__trace_summary_session_id_matches(self):
        summary = self.tracer.trace_summary(SESSION_ID)
        assert summary['session_id'] == SESSION_ID

    def test_5__trace_no_match_returns_empty(self):
        result = self.tracer.trace('nonexistent-session-xyz')
        assert result == []
