# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Kibana__Data_View__Result
# Result of ensure_data_view: the data view id (Kibana-generated UUID), a
# `created` flag distinguishing "we created it" from "it already existed",
# the HTTP status, and a diagnostic line on failure. Pure data.
#
# id is captured so a future dashboard generator can patch it into the
# `references` array of pre-built lens/visualization saved objects.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Diagnostic      import Safe_Str__Diagnostic


class Schema__Kibana__Data_View__Result(Type_Safe):
    id          : Safe_Str__Text                                                    # Empty when creation failed
    title       : Safe_Str__Text
    created     : bool                = False                                       # True when we POSTed; False when it already existed (or failed)
    http_status : int                 = 0
    error       : Safe_Str__Diagnostic
