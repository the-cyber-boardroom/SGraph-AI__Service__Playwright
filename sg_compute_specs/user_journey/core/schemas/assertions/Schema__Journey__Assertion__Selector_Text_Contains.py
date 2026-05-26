# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Assertion__Selector_Text_Contains
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous             import Safe_Str__Text__Dangerous

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Base               import Schema__Journey__Assertion__Base


class Schema__Journey__Assertion__Selector_Text_Contains(Schema__Journey__Assertion__Base):  # Selector text contains substring
    assertion_type : Enum__Assertion__Type = Enum__Assertion__Type.SELECTOR_TEXT_CONTAINS
    selector       : Safe_Str__Text__Dangerous                                      # Selector whose text is read
    expected       : Safe_Str__Text__Dangerous                                      # Substring the text must contain
