# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Dict__Assertion__Schemas__By_Type (assertion dispatcher registry)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict                               import Type_Safe__Dict

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type


class Dict__Assertion__Schemas__By_Type(Type_Safe__Dict):                           # Enum__Assertion__Type → Schema__Journey__Assertion__* class
    expected_key_type   = Enum__Assertion__Type
    expected_value_type = type
