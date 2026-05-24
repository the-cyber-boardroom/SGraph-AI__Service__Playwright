# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__Traffic__Generator
# run_local drives the real L1 (node) + L2 — node-gated, asserts 100% rule accuracy
# on the corpus. run_http drives a real loopback echo server (no Sentinel in front)
# — proving the measurement detects that malicious traffic reaches a bare origin.
# ═══════════════════════════════════════════════════════════════════════════════

import threading
from http.server import ThreadingHTTPServer
from unittest    import skipUnless

import sgraph_ai_service_playwright__cli.sentinel.traffic.echo.Echo__Server as echo_mod
from sgraph_ai_service_playwright__cli.sentinel.traffic.echo.Echo__Server               import _Echo_Handler
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source     import node_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness  import Sentinel__Local__Harness
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink    import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus          import Sentinel__Traffic__Corpus
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Generator       import Sentinel__Traffic__Generator
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Report__Builder import Sentinel__Traffic__Report__Builder


def _generator():
    return Sentinel__Traffic__Generator(harness=Sentinel__Local__Harness(log_sink=InMemory__Log__Sink()))


@skipUnless(node_available(), 'node not available')
class TestRunLocal:
    def test_corpus_is_classified_perfectly(self):
        results = _generator().run_local(Sentinel__Traffic__Corpus().cases())
        report  = Sentinel__Traffic__Report__Builder().build(results, mode='local')
        assert report.accuracy_pct == 100.0, [r.json() for r in results if not r.matched]
        assert report.malicious_blocked == report.malicious_total
        assert report.benign_allowed   == report.benign_total

    def test_observed_rule_matches_expected_for_blocks(self):
        results = _generator().run_local(Sentinel__Traffic__Corpus().cases())
        for r in results:
            if r.observed_verdict.value == 'block':
                assert str(r.observed_rule) == str(r.expected_rule), str(r.name)


class TestRunHttpAgainstBareOrigin:
    def test_bare_echo_origin_lets_everything_through(self):
        echo_mod._HITS.clear()
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), _Echo_Handler)
        port  = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            results = _generator().run_http(Sentinel__Traffic__Corpus().cases(), base_url=f'http://127.0.0.1:{port}')
            report  = Sentinel__Traffic__Report__Builder().build(results, mode='http')
            assert report.blocked == 0                                               # no edge → nothing blocked
            assert report.benign_allowed == report.benign_total
        finally:
            httpd.shutdown()
