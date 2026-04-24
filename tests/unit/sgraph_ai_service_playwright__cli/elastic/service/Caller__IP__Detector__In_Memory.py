# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Caller__IP__Detector__In_Memory
# Subclass that returns a fixed IP without hitting checkip.amazonaws.com.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector         import Caller__IP__Detector


class Caller__IP__Detector__In_Memory(Caller__IP__Detector):
    fixture_ip : str = '203.0.113.42'                                               # TEST-NET-3 RFC 5737 — never a real public IP

    def fetch(self) -> str:
        return self.fixture_ip + '\n'                                               # Real checkip response includes a trailing newline
