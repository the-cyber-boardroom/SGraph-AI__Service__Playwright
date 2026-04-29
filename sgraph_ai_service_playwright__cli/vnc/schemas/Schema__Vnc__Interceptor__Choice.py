# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vnc__Interceptor__Choice
# N5 selector for the mitmproxy interceptor a new stack should load at boot.
#
# Three valid shapes:
#   kind=NONE                                          → mitmproxy with no interceptor (default)
#   kind=NAME   + name='header_logger'                 → load /opt/interceptors/examples/{name}.py
#   kind=INLINE + inline_source='<raw Python source>'  → bake source at create time into
#                                                        /opt/interceptors/runtime/active.py
#
# Pure data; resolution into a usable script-on-disk path lives in the
# Vnc__Interceptor__Resolver helper (7e/7f).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Interceptor__Source import Safe_Str__Vnc__Interceptor__Source


class Schema__Vnc__Interceptor__Choice(Type_Safe):
    kind          : Enum__Vnc__Interceptor__Kind = Enum__Vnc__Interceptor__Kind.NONE
    name          : Safe_Str__Id                                                    # Set when kind=NAME — references baked example file
    inline_source : Safe_Str__Vnc__Interceptor__Source                              # Set when kind=INLINE — full Python source
