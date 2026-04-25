# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Seed__Request
# Inputs for `sp elastic seed NAME`. Generates N synthetic log docs spread over
# a window ending now, then posts them to the named stack's Elastic via the
# bulk API. Default matches the CLI default (10 000 docs / 7 days).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password    import Safe_Str__Elastic__Password


class Schema__Elastic__Seed__Request(Type_Safe):
    stack_name       : Safe_Str__Elastic__Stack__Name
    index            : Safe_Str__Id                  = 'sg-synthetic'
    document_count   : int                           = 10_000                       # Monitor timing — logged in the response
    window_days      : int                           = 7                            # Spread timestamps over the last N days ending now
    elastic_password : Safe_Str__Elastic__Password                                  # Empty → service reads from env var SG_ELASTIC_PASSWORD
    batch_size       : int                           = 1_000                        # _bulk body size per round trip
    create_data_view : bool                          = True                         # After bulk-post, ensure a Kibana data view points at the index — bypasses the "Now create a data view" wall in Discover
    time_field_name  : Safe_Str__Text                = 'timestamp'                  # The field the data view uses for time-based filtering / Discover histogram
