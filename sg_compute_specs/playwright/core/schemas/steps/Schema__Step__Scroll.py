# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Scroll (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int                                                 import Safe_Int

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Scroll(Schema__Step__Base):                                     # Scroll
    action              : Enum__Step__Action = Enum__Step__Action.SCROLL
    selector            : Safe_Str__Selector = None                                 # None = page scroll
    x                   : Safe_Int = 0
    y                   : Safe_Int = 0
