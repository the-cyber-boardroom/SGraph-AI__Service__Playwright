# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Assertion__Selector_Visible
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous             import Safe_Str__Text__Dangerous

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Base               import Schema__Journey__Assertion__Base


class Schema__Journey__Assertion__Selector_Visible(Schema__Journey__Assertion__Base):  # Selector appeared on the page
    assertion_type : Enum__Assertion__Type = Enum__Assertion__Type.SELECTOR_VISIBLE
    selector       : Safe_Str__Text__Dangerous                                      # CSS/text selector (preserves #.>[] chars)
