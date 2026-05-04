# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Schema__Vnc__Mitm__Flow__Summary
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url


class Schema__Vnc__Mitm__Flow__Summary(Type_Safe):
    flow_id        : Safe_Str__Id
    method         : Safe_Str__Id
    url            : Safe_Str__Url
    status_code    : int            = 0
    intercepted_at : Safe_Str__Text
