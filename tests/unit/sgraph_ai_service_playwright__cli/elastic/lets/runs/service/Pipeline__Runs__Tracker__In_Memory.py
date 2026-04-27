# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Pipeline__Runs__Tracker__In_Memory
# Real subclass that overrides record_run() to capture the call without
# touching Elastic.  Loader tests use this so existing http_client.bulk_calls
# assertions still describe just the data-path bulk-posts (not the journal write).
# No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from sgraph_ai_service_playwright__cli.elastic.lets.runs.schemas.Schema__Pipeline__Run            import Schema__Pipeline__Run
from sgraph_ai_service_playwright__cli.elastic.lets.runs.service.Pipeline__Runs__Tracker          import Pipeline__Runs__Tracker


class Pipeline__Runs__Tracker__In_Memory(Pipeline__Runs__Tracker):
    record_calls    : list                                                          # [(base_url, schema_dict_snapshot), ...]
    fixture_response: tuple                                                          # (created, updated, failed, http_status, error_msg) — empty → defaults to (1, 0, 0, 200, '')

    def record_run(self, base_url : str                  ,
                         username : str                  ,
                         password : str                  ,
                         record   : Schema__Pipeline__Run
                    ) -> Tuple[int, int, int, int, str]:
        # Capture a JSON snapshot so tests can assert on individual fields
        # without holding a reference to a record that the caller might mutate.
        self.record_calls.append((base_url, record.json()))
        if self.fixture_response:
            return self.fixture_response
        return 1, 0, 0, 200, ''                                                      # Default: one journal doc created OK
