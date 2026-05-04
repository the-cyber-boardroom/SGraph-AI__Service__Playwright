# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Fill (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Fill(Schema__Step__Base):                                       # Fill form field
    action              : Enum__Step__Action = Enum__Step__Action.FILL
    selector            : Safe_Str__Selector
    value               : Safe_Str__Text                                            # Up to 4 KB
    clear_first         : bool = True
