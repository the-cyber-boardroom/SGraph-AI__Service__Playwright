# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Schema__Elastic__Health__Check
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.elastic.enums.Enum__Health__Status                            import Enum__Health__Status
from sg_compute_specs.elastic.primitives.Safe_Str__Diagnostic                       import Safe_Str__Diagnostic


class Schema__Elastic__Health__Check(Type_Safe):
    name   : Safe_Str__Text
    status : Enum__Health__Status = Enum__Health__Status.SKIP
    detail : Safe_Str__Diagnostic
