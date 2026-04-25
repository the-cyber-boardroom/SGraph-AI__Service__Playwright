# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Kibana__Saved_Objects__Client__In_Memory
# Real subclass for the saved-objects client. Records every ensure_data_view
# call and returns a canned result so the seed_stack tests don't hit the
# network. No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Data_View__Result import Schema__Kibana__Data_View__Result
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client    import Kibana__Saved_Objects__Client


class Kibana__Saved_Objects__Client__In_Memory(Kibana__Saved_Objects__Client):
    ensure_calls       : list                                                       # [(base_url, title, time_field), ...]
    delete_calls       : list                                                       # [(base_url, title), ...] — wipe path
    fixture_view_id    : str  = 'dv-fixture-uuid'                                   # Returned by the next ensure_data_view call
    fixture_created    : bool = True                                                # True → "we created it", False → "already existed"
    fixture_error      : str  = ''                                                  # Non-empty makes ensure_data_view return a failure result
    fixture_view_existed_for_delete : bool = True                                   # Drives delete_data_view_by_title return value

    def ensure_data_view(self, base_url        : str ,
                                username        : str ,
                                password        : str ,
                                title           : str ,
                                time_field_name : str = 'timestamp'
                          ) -> Schema__Kibana__Data_View__Result:
        self.ensure_calls.append((base_url, title, time_field_name))
        if self.fixture_error:
            return Schema__Kibana__Data_View__Result(title       = title              ,
                                                     http_status = 0                  ,
                                                     error       = self.fixture_error )
        return Schema__Kibana__Data_View__Result(id          = self.fixture_view_id ,
                                                 title       = title                ,
                                                 created     = bool(self.fixture_created),
                                                 http_status = 200                  ,
                                                 error       = ''                   )

    def delete_data_view_by_title(self, base_url: str, username: str, password: str, title: str) -> Tuple[bool, int, str]:
        self.delete_calls.append((base_url, title))
        return bool(self.fixture_view_existed_for_delete), 200, ''
