# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — List__Sequence__Steps (spec §6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List                               import Type_Safe__List

from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class List__Sequence__Steps(Type_Safe__List):                                       # Parsed step list
    expected_type = Schema__Step__Base
