# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Kibana__Saved_Objects__Client__In_Memory
# Real subclass for the saved-objects client. Records every ensure_data_view
# call and returns a canned result so the seed_stack tests don't hit the
# network. No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Tuple

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Dashboard__Result import Schema__Kibana__Dashboard__Result
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Data_View__Result import Schema__Kibana__Data_View__Result
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client    import Kibana__Saved_Objects__Client


class Kibana__Saved_Objects__Client__In_Memory(Kibana__Saved_Objects__Client):
    ensure_calls       : list                                                       # [(base_url, title, time_field), ...]
    delete_calls       : list                                                       # [(base_url, title), ...] — wipe path
    dashboard_calls    : list                                                       # [(base_url, index, data_view_id, time_field), ...]
    fixture_view_id    : str  = 'dv-fixture-uuid'                                   # Returned by the next ensure_data_view call
    fixture_created    : bool = True                                                # True → "we created it", False → "already existed"
    fixture_error      : str  = ''                                                  # Non-empty makes ensure_data_view return a failure result
    fixture_view_existed_for_delete : bool = True                                   # Drives delete_data_view_by_title return value
    fixture_dashboard_objects : int  = 5                                            # Returned object_count from ensure_default_dashboard
    fixture_dashboard_error   : str  = ''
    harden_calls              : list                                                 # [(base_url, space_id, features), ...]
    fixture_harden_error      : str  = ''
    delete_object_calls       : list                                                 # [(base_url, [(type, id), ...]), ...]
    fixture_delete_object_count : int = 0                                            # What delete_saved_objects returns
    import_calls              : list                                                 # [(base_url, ndjson_byte_count, overwrite), ...] — populated by import_objects (used by the LETS-inventory dashboard import)
    fixture_import_success_count : int = 6                                           # What import_objects' Schema__Kibana__Import__Result.success_count carries (default 6 = 1 dashboard + 5 visualisations)
    find_calls                : list                                                 # [(base_url, object_type, page_size), ...]
    fixture_find_objects      : dict                                                 # {object_type_str: [{'id': ..., 'type': ..., 'title': ..., 'updated_at': ...}, ...]} — populated by find()

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

    def disable_space_features(self, base_url: str, username: str, password: str,
                                      space_id: str = 'default', features: list = None) -> Tuple[bool, int, str]:
        self.harden_calls.append((base_url, space_id, list(features) if features else None))
        if self.fixture_harden_error:
            return False, 0, self.fixture_harden_error
        return True, 200, ''

    def delete_saved_objects(self, base_url: str, username: str, password: str, objects: list) -> int:
        self.delete_object_calls.append((base_url, list(objects)))
        return int(self.fixture_delete_object_count)

    def delete_default_dashboard_objects(self, base_url: str, username: str, password: str) -> int:
        return self.delete_saved_objects(base_url, username, password, [])

    # ─── import_objects override (added for the LETS-inventory dashboard) ─────
    # The synthetic-data dashboard reaches Kibana through ensure_default_dashboard
    # which is overridden above.  The CF-inventory dashboard imports its
    # ndjson directly via import_objects, so we add a fixture-driven override
    # here.  Records every call so tests can assert on what was imported.

    def find(self, base_url     : str ,
                   username     : str ,
                   password     : str ,
                   object_type        ,                                             # Enum__Saved_Object__Type — string-coerced via str() to lookup in the fixture dict
                   page_size    : int = 100):
        from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Kibana__Saved_Object import List__Schema__Kibana__Saved_Object
        from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Find__Response          import Schema__Kibana__Find__Response
        from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Saved_Object            import Schema__Kibana__Saved_Object
        self.find_calls.append((base_url, str(object_type), page_size))
        objects = List__Schema__Kibana__Saved_Object()
        for raw in self.fixture_find_objects.get(str(object_type), []):
            objects.append(Schema__Kibana__Saved_Object(id         = str(raw.get('id'        , '')),
                                                        type       = str(raw.get('type'      , '')),
                                                        title      = str(raw.get('title'     , '')),
                                                        updated_at = str(raw.get('updated_at', ''))))
        return Schema__Kibana__Find__Response(total       = len(objects)             ,
                                              objects     = objects                  ,
                                              http_status = 200                      ,
                                              error       = ''                       )

    def import_objects(self, base_url     : str   ,
                              username     : str   ,
                              password     : str   ,
                              ndjson_bytes : bytes ,
                              overwrite    : bool  = True
                        ):
        from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Import__Result import Schema__Kibana__Import__Result
        self.import_calls.append((base_url, len(ndjson_bytes), bool(overwrite)))
        return Schema__Kibana__Import__Result(success       = True                            ,
                                              success_count = int(self.fixture_import_success_count),
                                              error_count   = 0                               ,
                                              http_status   = 200                             ,
                                              first_error   = ''                              )

    def ensure_default_dashboard(self, base_url     : str ,
                                        username     : str ,
                                        password     : str ,
                                        index        : str ,
                                        data_view_id : str ,
                                        time_field   : str = 'timestamp'
                                  ) -> Schema__Kibana__Dashboard__Result:
        self.dashboard_calls.append((base_url, index, data_view_id, time_field))
        if self.fixture_dashboard_error:
            return Schema__Kibana__Dashboard__Result(id          = 'sg-synthetic-overview',
                                                     title       = 'Synthetic Logs Overview',
                                                     http_status = 0,
                                                     error       = self.fixture_dashboard_error)
        return Schema__Kibana__Dashboard__Result(id           = 'sg-synthetic-overview'   ,
                                                 title        = 'Synthetic Logs Overview' ,
                                                 object_count = int(self.fixture_dashboard_objects),
                                                 created      = True                       ,
                                                 http_status  = 200                        ,
                                                 error        = ''                         )
