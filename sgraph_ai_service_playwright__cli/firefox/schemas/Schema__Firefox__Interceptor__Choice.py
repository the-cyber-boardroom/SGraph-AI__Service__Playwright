# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Interceptor__Choice
# Selector for the mitmproxy interceptor a new Firefox stack loads at boot.
#
#   kind=NONE                                          → mitmproxy with no interceptor (default)
#   kind=NAME   + name='header_logger'                 → baked example
#   kind=INLINE + inline_source='<raw Python source>'  → operator-supplied source
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Firefox__Interceptor__Kind       import Enum__Firefox__Interceptor__Kind
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Interceptor__Source import Safe_Str__Firefox__Interceptor__Source


class Schema__Firefox__Interceptor__Choice(Type_Safe):
    kind          : Enum__Firefox__Interceptor__Kind = Enum__Firefox__Interceptor__Kind.NONE
    name          : Safe_Str__Id                                                     # Set when kind=NAME
    inline_source : Safe_Str__Firefox__Interceptor__Source                           # Set when kind=INLINE — full Python source
