# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Wait_For (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Wait__State                                   import Enum__Wait__State
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Wait_For(Schema__Step__Base):                                   # Wait for condition
    action              : Enum__Step__Action = Enum__Step__Action.WAIT_FOR
    selector            : Safe_Str__Selector = None                                 # Wait for selector (if provided)
    url_pattern         : Safe_Str__Url      = None                                 # Wait for URL match
    state               : Enum__Wait__State  = None                                 # Wait for page state
    visible             : bool               = True                                 # For selector waits: visible vs attached
