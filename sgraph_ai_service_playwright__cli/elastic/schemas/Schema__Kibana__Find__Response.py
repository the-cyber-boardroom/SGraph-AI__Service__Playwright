# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Kibana__Find__Response
# Wraps the result of Kibana's /api/saved_objects/_find call. Carries the
# total saved-object count plus the per-page list of objects, plus an HTTP
# status + diagnostic so callers can distinguish "no results" from "auth
# failed" without re-walking the items list.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Kibana__Saved_Object import List__Schema__Kibana__Saved_Object
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Diagnostic      import Safe_Str__Diagnostic


class Schema__Kibana__Find__Response(Type_Safe):
    total       : int                                = 0
    objects     : List__Schema__Kibana__Saved_Object
    http_status : int                                = 0
    error       : Safe_Str__Diagnostic                                              # Empty on success; otherwise "HTTP 401: <body snippet>"
