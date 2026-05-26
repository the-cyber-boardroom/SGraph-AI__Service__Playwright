# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Assertion__Result (one assertion's outcome)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous             import Safe_Str__Text__Dangerous

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Status                            import Enum__Assertion__Status
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Assertion_Id                     import Assertion_Id


class Schema__Journey__Assertion__Result(Type_Safe):                                # One assertion's outcome
    assertion_id   : Assertion_Id          = None
    assertion_type : Enum__Assertion__Type = None
    status         : Enum__Assertion__Status
    expected       : Safe_Str__Text__Dangerous = None                               # What the assertion wanted (faithful display)
    actual         : Safe_Str__Text__Dangerous = None                               # What was observed (faithful display)
    error_message  : Safe_Str__Text            = None                               # Populated on ERROR
