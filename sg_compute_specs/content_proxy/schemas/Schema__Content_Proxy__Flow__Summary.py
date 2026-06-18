# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Flow__Summary
# One-line summary of a flow that transited a proxy. Pure data. Derived from the
# x-proxy-* headers the interceptor stamps.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy                 import Enum__Content_Proxy__Proxy


class Schema__Content_Proxy__Flow__Summary(Type_Safe):
    via               : Enum__Content_Proxy__Proxy        = Enum__Content_Proxy__Proxy.INT
    method            : Safe_Str__Text
    host              : Safe_Str__Text
    path              : Safe_Str__Text
    status_code       : int                               = 0
    action            : Enum__Content_Proxy__Flow__Action = Enum__Content_Proxy__Flow__Action.PASSED
    fastapi_connected : bool                              = False
    request_id        : Safe_Str__Text
