# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Press (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Keyboard__Key                                 import Enum__Keyboard__Key
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Press(Schema__Step__Base):                                      # Keyboard press
    action              : Enum__Step__Action = Enum__Step__Action.PRESS
    selector            : Safe_Str__Selector = None                                 # If None, press on active element
    key                 : Enum__Keyboard__Key                                       # e.g. Enum__Keyboard__Key.ENTER
