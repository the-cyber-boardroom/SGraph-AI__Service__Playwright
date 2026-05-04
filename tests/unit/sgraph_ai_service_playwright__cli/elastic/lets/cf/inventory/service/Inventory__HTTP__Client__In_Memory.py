# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__HTTP__Client__In_Memory
# Real subclass for the LETS-inventory HTTP client. Overrides bulk_post_with_id
# directly (mirrors the pattern in Elastic__HTTP__Client__In_Memory which
# overrides bulk_post() rather than the lower-level request() seam). Records
# every call for assertions and returns a fixture tuple.
# Updated for Phase 2 ES optimisations: bulk_calls records the new optional
# params (refresh, routing, max_bytes); new methods for E-4/E-6 are stubbed.
# No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client


class Inventory__HTTP__Client__In_Memory(Inventory__HTTP__Client):
    bulk_calls            : list                                                    # [(base_url, index, doc_count, id_field), ...] — backward-compat 4-tuple
    bulk_calls_opts       : list                                                    # [(refresh, routing, max_bytes, wait_for_active_shards), ...] — E-1/2/5/7 params
    fixture_response      : tuple                                                   # (created, updated, failed, http_status, error_msg) — empty → defaults to (len(docs), 0, 0, 200, '')
    delete_pattern_calls  : list                                                    # [(base_url, pattern), ...]
    fixture_delete_pattern_response : tuple                                          # (indices_dropped, http_status, error_msg) — empty → (0, 200, '')
    count_pattern_calls   : list                                                    # [(base_url, pattern), ...]
    fixture_count_response : tuple                                                  # (count, http_status, error_msg) — empty → (0, 200, '')
    aggregate_calls       : list                                                    # [(base_url, index_pattern, top_n), ...]
    fixture_run_buckets   : list                                                    # Raw ES aggregation buckets returned by aggregate_run_summaries
    terms_update_calls    : list                                                    # [(base_url, index_pattern, field, len(values), script_source), ...]
    refresh_calls         : list                                                    # [(base_url, index_pattern), ...]
    template_calls        : list                                                    # [(base_url, template_name, index_pattern), ...]

    def bulk_post_with_id(self, base_url               : str             ,
                                username               : str             ,
                                password               : str             ,
                                index                  : str             ,
                                docs                   : Type_Safe__List  ,
                                id_field               : str  = 'etag'   ,
                                refresh                : bool = True      ,
                                routing                : str  = ''        ,
                                max_bytes              : int  = 0         ,
                                wait_for_active_shards : str  = 'null'    ,
                          ) -> Tuple[int, int, int, int, str]:
        self.bulk_calls.append((base_url, index, len(docs), id_field))
        self.bulk_calls_opts.append((refresh, routing, max_bytes, wait_for_active_shards))
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

    def update_by_query_terms(self, base_url      : str  ,
                                     username      : str  ,
                                     password      : str  ,
                                     index_pattern : str  ,
                                     field         : str  ,
                                     values        : list ,
                                     script_source : str  ,
                                     script_params : dict = None
                               ) -> Tuple[int, int, str]:
        self.terms_update_calls.append((base_url, index_pattern, field, len(values), script_source))
        return len(values), 200, ''                                                 # Default: all docs updated

    def trigger_refresh(self, base_url      : str ,
                               username      : str ,
                               password      : str ,
                               index_pattern : str
                         ) -> Tuple[int, str]:
        self.refresh_calls.append((base_url, index_pattern))
        return 200, ''

    def ensure_index_template(self, base_url      : str  ,
                                      username      : str  ,
                                      password      : str  ,
                                      template_name : str  ,
                                      index_pattern : str  ,
                                      mappings      : dict
                               ) -> Tuple[int, str]:
        self.template_calls.append((base_url, template_name, index_pattern))
        return 200, ''
