# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the traffic corpus + the pure report builder (no node, no HTTP)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict                       import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.traffic.enums.Enum__Traffic__Category               import Enum__Traffic__Category
from sgraph_ai_service_playwright__cli.sentinel.traffic.schemas.List__Schema__Traffic__Result        import List__Schema__Traffic__Result
from sgraph_ai_service_playwright__cli.sentinel.traffic.schemas.Schema__Traffic__Result              import Schema__Traffic__Result
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus            import Sentinel__Traffic__Corpus
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Report__Builder   import Sentinel__Traffic__Report__Builder

BLOCK = Enum__Sentinel__Verdict.BLOCK
ALLOW = Enum__Sentinel__Verdict.ALLOW


class TestCorpus:
    def test_has_benign_and_malicious_and_malformed(self):
        cases = Sentinel__Traffic__Corpus().cases()
        cats  = {c.category for c in cases}
        assert Enum__Traffic__Category.BENIGN    in cats
        assert Enum__Traffic__Category.MALICIOUS in cats
        assert Enum__Traffic__Category.MALFORMED in cats

    def test_covers_every_block_rule(self):
        rules = {str(c.expected_rule) for c in Sentinel__Traffic__Corpus().cases() if c.expected_verdict == BLOCK}
        assert {'0003', '0007', '0012', '0014', '0018'}.issubset(rules)


def _result(category, expected, observed, latency) -> Schema__Traffic__Result:
    return Schema__Traffic__Result(name='c', category=category, expected_verdict=expected,
                                   observed_verdict=observed, latency_ms=latency, matched=(expected == observed))


class TestReportBuilder:
    def test_perfect_run(self):
        results = List__Schema__Traffic__Result()
        results.append(_result(Enum__Traffic__Category.BENIGN,    ALLOW, ALLOW, 10.0))
        results.append(_result(Enum__Traffic__Category.MALICIOUS, BLOCK, BLOCK, 20.0))
        report = Sentinel__Traffic__Report__Builder().build(results, mode='local')
        assert report.total == 2 and report.accuracy_pct == 100.0
        assert report.malicious_blocked == 1 and report.malicious_total == 1
        assert report.benign_allowed == 1 and report.benign_total == 1
        assert report.latency_min_ms == 10.0 and report.latency_max_ms == 20.0

    def test_baseline_no_sentinel_lets_malicious_through(self):
        # what `send` against a bare echo server looks like: everything returns allow
        results = List__Schema__Traffic__Result()
        results.append(_result(Enum__Traffic__Category.BENIGN,    ALLOW, ALLOW, 5.0))
        results.append(_result(Enum__Traffic__Category.MALICIOUS, BLOCK, ALLOW, 6.0))
        report = Sentinel__Traffic__Report__Builder().build(results, mode='http')
        assert report.malicious_blocked == 0                                         # no edge in front → bad traffic reaches origin
        assert report.accuracy_pct == 50.0
