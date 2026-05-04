# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Set_Viewport (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.browser.Schema__Viewport                                  import Schema__Viewport
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Set_Viewport(Schema__Step__Base):                               # Change viewport
    action              : Enum__Step__Action = Enum__Step__Action.SET_VIEWPORT
    viewport            : Schema__Viewport
