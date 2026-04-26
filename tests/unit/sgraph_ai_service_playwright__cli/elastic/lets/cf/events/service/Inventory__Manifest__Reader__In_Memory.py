# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__Manifest__Reader__In_Memory
# Real subclass that returns canned dicts from fixture_unprocessed_docs.
# Records every list_unprocessed call so loader tests can assert what queue
# was built.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List, Tuple

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader import Inventory__Manifest__Reader


class Inventory__Manifest__Reader__In_Memory(Inventory__Manifest__Reader):
    fixture_unprocessed_docs : list                                                 # [{'bucket', 'key', 'etag', 'size_bytes', 'delivery_at'}, ...]
    list_calls               : list                                                 # [(base_url, top_n), ...]
    fixture_response         : tuple                                                # (docs, http_status, error_msg) — empty → uses fixture_unprocessed_docs

    def list_unprocessed(self, base_url : str ,
                                username : str ,
                                password : str ,
                                top_n    : int = 100
                          ) -> Tuple[List[dict], int, str]:
        self.list_calls.append((base_url, top_n))
        if self.fixture_response:
            return self.fixture_response
        # Apply top_n cap to fixture
        return list(self.fixture_unprocessed_docs)[:top_n], 200, ''
