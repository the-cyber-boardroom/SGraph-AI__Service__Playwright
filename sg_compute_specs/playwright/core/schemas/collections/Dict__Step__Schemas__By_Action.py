# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Dict__Step__Schemas__By_Action (spec §6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict                               import Type_Safe__Dict

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action


class Dict__Step__Schemas__By_Action(Type_Safe__Dict):                              # Dispatcher registry
    expected_key_type   = Enum__Step__Action
    expected_value_type = type                                                      # A Schema__Step__* class
