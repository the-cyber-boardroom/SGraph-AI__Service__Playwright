# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__HTTP__Client__In_Memory
# Real subclass for the LETS-inventory HTTP client. Overrides bulk_post_with_id
# directly (mirrors the pattern in Elastic__HTTP__Client__In_Memory which
# overrides bulk_post() rather than the lower-level request() seam). Records
# every call for assertions and returns a fixture tuple.
# No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client


class Inventory__HTTP__Client__In_Memory(Inventory__HTTP__Client):
    bulk_calls            : list                                                    # [(base_url, index, doc_count, id_field), ...]
    fixture_response      : tuple                                                   # (created, updated, failed, http_status, error_msg) — empty → defaults to (len(docs), 0, 0, 200, '')
    delete_pattern_calls  : list                                                    # [(base_url, pattern), ...]
    fixture_delete_pattern_response : tuple                                          # (indices_dropped, http_status, error_msg) — empty → (0, 200, '')
    count_pattern_calls   : list                                                    # [(base_url, pattern), ...]
    fixture_count_response : tuple                                                  # (count, http_status, error_msg) — empty → (0, 200, '')
    aggregate_calls       : list                                                    # [(base_url, index_pattern, top_n), ...]
    fixture_run_buckets   : list                                                    # Raw ES aggregation buckets returned by aggregate_run_summaries

    def bulk_post_with_id(self, base_url : str              ,
                                username : str              ,
                                password : str              ,
                                index    : str              ,
                                docs     : Type_Safe__List   ,
                                id_field : str              = 'etag'
                          ) -> Tuple[int, int, int, int, str]:
        self.bulk_calls.append((base_url, index, len(docs), id_field))
        if self.fixture_response:
            return self.fixture_response
        return len(docs), 0, 0, 200, ''                                             # Default: every doc created OK

    def delete_indices_by_pattern(self, base_url : str ,
                                         username : str ,
                                         password : str ,
                                         pattern  : str
                                    ) -> Tuple[int, int, str]:
        self.delete_pattern_calls.append((base_url, pattern))
        if self.fixture_delete_pattern_response:
            return self.fixture_delete_pattern_response
        return 0, 200, ''                                                           # Default: no matching indices to delete

    def count_indices_by_pattern(self, base_url : str ,
                                        username : str ,
                                        password : str ,
                                        pattern  : str
                                  ) -> Tuple[int, int, str]:
        self.count_pattern_calls.append((base_url, pattern))
        if self.fixture_count_response:
            return self.fixture_count_response
        return 0, 200, ''

    def aggregate_run_summaries(self, base_url      : str ,
                                       username      : str ,
                                       password      : str ,
                                       index_pattern : str ,
                                       top_n         : int = 100
                                  ) -> Tuple[list, int, str]:
        self.aggregate_calls.append((base_url, index_pattern, top_n))
        return list(self.fixture_run_buckets), 200, ''
