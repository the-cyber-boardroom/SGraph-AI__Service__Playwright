# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Traffic__Generator
# Replays a use-case corpus two ways and records results for measurement:
#   • run_local — in-process through the real L1 (node) + L2 enforce. The faithful
#     rule tester: observes verdict/rule/enforcement-status per case. Latency is the
#     harness cost (node subprocess), NOT the CloudFront runtime — use it for
#     accuracy + relative comparison, not absolute edge latency.
#   • run_http — real HTTP at any target (the httpget echo server or a live CF
#     distribution). Measures end-to-end status + latency; verdict is inferred from
#     the HTTP status (>=400 → block). HTTP clients normalise '..' so traversal/
#     malformed cases are best covered by run_local.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict             import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer2.Sentinel__L2__Actor        import Sentinel__L2__Actor
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness    import Sentinel__Local__Harness
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink      import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.traffic.schemas.List__Schema__Traffic__Result import List__Schema__Traffic__Result
from sgraph_ai_service_playwright__cli.sentinel.traffic.schemas.Schema__Traffic__Result      import Schema__Traffic__Result

BLOCK = Enum__Sentinel__Verdict.BLOCK
ALLOW = Enum__Sentinel__Verdict.ALLOW


class Sentinel__Traffic__Generator(Type_Safe):
    harness : Sentinel__Local__Harness

    def _result(self, case, observed_verdict, observed_rule, http_status, latency_ms) -> Schema__Traffic__Result:
        return Schema__Traffic__Result(name=str(case.name), category=case.category,
                                       expected_verdict=case.expected_verdict, observed_verdict=observed_verdict,
                                       expected_rule=str(case.expected_rule), observed_rule=str(observed_rule),
                                       http_status=http_status, latency_ms=latency_ms,
                                       matched=(observed_verdict == case.expected_verdict))

    def run_local(self, cases, repeat: int = 1) -> List__Schema__Traffic__Result:
        actor   = Sentinel__L2__Actor(log_sink=InMemory__Log__Sink())
        results = List__Schema__Traffic__Result()
        for _ in range(max(1, repeat)):
            for case in cases:
                captured = self.harness.build_captured(str(case.method), str(case.path), str(case.source_ip))
                t0       = time.perf_counter()
                signal   = self.harness.evaluate_signal(captured)
                enforce  = actor.enforce(signal)
                latency  = (time.perf_counter() - t0) * 1000.0
                results.append(self._result(case, signal.verdict, signal.rule_id, enforce.http_status, latency))
        return results

    def run_http(self, cases, base_url: str, repeat: int = 1) -> List__Schema__Traffic__Result:
        import requests
        base    = base_url.rstrip('/')
        results = List__Schema__Traffic__Result()
        for _ in range(max(1, repeat)):
            for case in cases:
                url     = base + (str(case.path) or '/')
                headers = {'X-Forwarded-For': str(case.source_ip)}                   # spoof source IP for the edge / echo server
                t0      = time.perf_counter()
                try:
                    resp   = requests.request(str(case.method) or 'GET', url, headers=headers,
                                              allow_redirects=False, timeout=15)
                    status = resp.status_code
                except requests.RequestException:
                    status = 0
                latency  = (time.perf_counter() - t0) * 1000.0
                verdict  = BLOCK if status >= 400 else ALLOW
                results.append(self._result(case, verdict, '', status, latency))
        return results
