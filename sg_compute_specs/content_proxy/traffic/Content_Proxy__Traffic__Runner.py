# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Traffic__Runner
# Replays the corpus through the workflow and grades each case. The grading
# (build_results) is PURE and unit-tested; run() drives a caller-supplied
# transform callable (live = sg-playwright through mitmproxy-int) → integration.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
from sg_compute_specs.content_proxy.traffic.Schema__Content_Proxy__Traffic__Result   import Schema__Content_Proxy__Traffic__Result


class Content_Proxy__Traffic__Runner(Type_Safe):

    def build_results(self, cases, observed) -> list:                              # observed: {case_name: (Enum action, latency_ms)}
        results = []
        for c in cases:
            action, latency = observed.get(str(c.name),
                                           (Enum__Content_Proxy__Flow__Action.PASSED, 0))
            results.append(Schema__Content_Proxy__Traffic__Result(
                case_name  = c.name                ,
                label      = c.label               ,
                expected   = c.expected            ,
                observed   = action                ,
                passed     = (action == c.expected),
                latency_ms = int(latency)          ))
        return results

    def run(self, cases, transform) -> list:                                       # transform(case) -> (Enum action, latency_ms) — INTEGRATION
        observed = {}
        for c in cases:
            observed[str(c.name)] = transform(c)
        return self.build_results(cases, observed)
