# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Click (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt

from sg_compute_specs.playwright.core.schemas.enums.Enum__Mouse__Button                                 import Enum__Mouse__Button
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Click(Schema__Step__Base):                                      # Click element
    action              : Enum__Step__Action   = Enum__Step__Action.CLICK
    selector            : Safe_Str__Selector
    button              : Enum__Mouse__Button  = Enum__Mouse__Button.LEFT
    click_count         : Safe_UInt            = 1
    delay_ms            : Safe_UInt__Milliseconds = 0
    force               : bool                 = False                              # Bypass actionability checks
