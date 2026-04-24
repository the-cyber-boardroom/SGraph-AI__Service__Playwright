# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Log__Document
# One synthetic log document produced by Synthetic__Data__Generator and posted
# to Elasticsearch via the bulk API. Intentionally log-shaped (timestamp /
# level / service / host / user / message) so Kibana's default Discover view
# renders something recognisable without custom index patterns.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Log__Level               import Enum__Log__Level


class Schema__Log__Document(Type_Safe):
    timestamp   : Safe_Str__Text                                                    # ISO-8601 UTC with millisecond precision — ES parses "date" type directly
    level       : Enum__Log__Level
    service     : Safe_Str__Id
    host        : Safe_Str__Id
    user        : Safe_Str__Id
    message     : Safe_Str__Text
    duration_ms : int           = 0
