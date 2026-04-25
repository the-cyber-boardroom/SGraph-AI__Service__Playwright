# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Elastic__HTTP__Client__In_Memory
# Real subclass that records every call and returns canned responses. The seed
# tests need it to exercise bulk_post without a live Elastic. No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Log__Document   import List__Schema__Log__Document
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Kibana__Probe__Status    import Enum__Kibana__Probe__Status
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client        import Elastic__HTTP__Client


class Elastic__HTTP__Client__In_Memory(Elastic__HTTP__Client):
    fixture_kibana_ready   : bool                                                   # What kibana_ready() returns
    fixture_probe_sequence : list                                                   # Queue of Enum__Kibana__Probe__Status values consumed by kibana_probe(); empty → falls back to fixture_kibana_ready
    bulk_calls             : list                                                   # [(base_url, index, doc_count), ...]

    def kibana_ready(self, base_url: str) -> bool:
        return bool(self.fixture_kibana_ready)

    def kibana_probe(self, base_url: str) -> Enum__Kibana__Probe__Status:           # Returns the next queued status; back-compat default uses fixture_kibana_ready
        if self.fixture_probe_sequence:
            return self.fixture_probe_sequence.pop(0)
        return Enum__Kibana__Probe__Status.READY if self.fixture_kibana_ready else Enum__Kibana__Probe__Status.UPSTREAM_DOWN

    def bulk_post(self, base_url : str                          ,
                        username : str                          ,
                        password : str                          ,
                        index    : str                          ,
                        docs     : List__Schema__Log__Document
                   ) -> Tuple[int, int, int, str]:
        self.bulk_calls.append((base_url, index, len(docs)))
        return len(docs), 0, 200, ''                                                # Always succeeds in fixture mode
