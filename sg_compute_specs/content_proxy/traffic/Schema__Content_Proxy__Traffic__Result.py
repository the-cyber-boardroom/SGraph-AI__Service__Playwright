# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Traffic__Result
# Outcome of replaying one corpus case through the workflow.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action


class Schema__Content_Proxy__Traffic__Result(Type_Safe):
    case_name  : Safe_Str__Text
    label      : Safe_Str__Text
    expected   : Enum__Content_Proxy__Flow__Action = Enum__Content_Proxy__Flow__Action.PASSED
    observed   : Enum__Content_Proxy__Flow__Action = Enum__Content_Proxy__Flow__Action.PASSED
    passed     : bool = False
    latency_ms : int  = 0
