# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Hover (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Hover(Schema__Step__Base):                                      # Mouse hover
    action              : Enum__Step__Action = Enum__Step__Action.HOVER
    selector            : Safe_Str__Selector
