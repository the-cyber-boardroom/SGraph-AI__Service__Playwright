# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Schema__Firefox__Interceptor__Choice
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sg_compute_specs.firefox.enums.Enum__Firefox__Interceptor__Kind                import Enum__Firefox__Interceptor__Kind
from sg_compute_specs.firefox.primitives.Safe_Str__Firefox__Interceptor__Source     import Safe_Str__Firefox__Interceptor__Source


class Schema__Firefox__Interceptor__Choice(Type_Safe):
    kind          : Enum__Firefox__Interceptor__Kind = Enum__Firefox__Interceptor__Kind.NONE
    name          : Safe_Str__Id
    inline_source : Safe_Str__Firefox__Interceptor__Source
