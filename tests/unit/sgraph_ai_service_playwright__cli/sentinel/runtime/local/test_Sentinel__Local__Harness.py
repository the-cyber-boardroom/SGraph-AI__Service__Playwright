# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__Local__Harness (Target B, local-direct, end-to-end)
# The real node L1 engine + the real Python L2 actor + an in-memory sink. node-gated.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import skipUnless

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict          import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source    import node_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness import Sentinel__Local__Harness
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink   import InMemory__Log__Sink


def _harness() -> Sentinel__Local__Harness:
    return Sentinel__Local__Harness(log_sink=InMemory__Log__Sink())


@skipUnless(node_available(), 'node not available')
class TestUseCase1Logging:
    def test_benign_request_is_logged_and_allowed(self):
        h = _harness()
        signal, enforce = h.hit('GET', '/index.html', source_ip='198.51.100.2')
        assert signal.verdict     == Enum__Sentinel__Verdict.ALLOW
        assert enforce.pass_to_origin is True
        records = h.log_sink.read_all()
        assert len(records) == 1
        assert str(records[0].rule_id) == '0001'

    def test_record_is_replayable_with_request_fields(self):
        h = _harness()
        signal, _ = h.hit('GET', '/index.html', source_ip='198.51.100.2')
        rec = h.log_sink.get(str(signal.request_id))
        assert str(rec.path)   == '/index.html'
        assert str(rec.method) == 'GET'


@skipUnless(node_available(), 'node not available')
class TestUseCase2Blocking:
    def test_etc_passwd_is_blocked_403_with_reason(self):
        h = _harness()
        signal, enforce = h.hit('GET', '/etc/passwd', source_ip='185.10.10.10')
        assert signal.verdict      == Enum__Sentinel__Verdict.BLOCK
        assert enforce.http_status == 403
        rec = h.log_sink.read_all()[0]
        assert str(rec.rule_id) == '0012'
        assert str(rec.reason)  == 'path never valid'
        assert rec.enforced is True

    def test_hidden_file_is_deflected_404(self):
        _, enforce = _harness().hit('GET', '/.env', source_ip='77.30.30.30')
        assert enforce.http_status == 404

    def test_banned_ip_is_blocked(self):
        signal, enforce = _harness().hit('GET', '/index.html', source_ip='10.0.0.6')
        assert signal.verdict      == Enum__Sentinel__Verdict.BLOCK
        assert str(signal.rule_id) == '0003'
        assert enforce.http_status == 403

    def test_source_ip_is_hashed_in_record_by_default(self):
        h = _harness()
        h.hit('GET', '/etc/passwd', source_ip='185.10.10.10')
        assert str(h.log_sink.read_all()[0].source_ip) != '185.10.10.10'
