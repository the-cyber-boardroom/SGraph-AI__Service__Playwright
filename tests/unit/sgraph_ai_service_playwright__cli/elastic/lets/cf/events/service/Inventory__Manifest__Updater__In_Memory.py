# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__Manifest__Updater__In_Memory
# Records every mark_processed and reset_all_processed call.  Returns
# fixture-driven (updated_count, http_status, error) tuples.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater import Inventory__Manifest__Updater


class Inventory__Manifest__Updater__In_Memory(Inventory__Manifest__Updater):
    mark_calls         : list                                                       # [(base_url, etag, run_id), ...]
    reset_calls        : list                                                       # [(base_url,), ...]
    fixture_mark_count : int = 1                                                    # What mark_processed returns as updated_count (default: 1 doc updated)
    fixture_reset_count: int = 0                                                    # What reset_all_processed returns
    fixture_mark_error : str = ''
    fixture_reset_error: str = ''

    def mark_processed(self, base_url : str ,
                              username : str ,
                              password : str ,
                              etag     : str ,
                              run_id   : str
                        ) -> Tuple[int, int, str]:
        self.mark_calls.append((base_url, etag, run_id))
        if self.fixture_mark_error:
            return 0, 0, self.fixture_mark_error
        return int(self.fixture_mark_count), 200, ''

    def reset_all_processed(self, base_url : str ,
                                   username : str ,
                                   password : str
                              ) -> Tuple[int, int, str]:
        self.reset_calls.append((base_url,))
        if self.fixture_reset_error:
            return 0, 0, self.fixture_reset_error
        return int(self.fixture_reset_count), 200, ''
