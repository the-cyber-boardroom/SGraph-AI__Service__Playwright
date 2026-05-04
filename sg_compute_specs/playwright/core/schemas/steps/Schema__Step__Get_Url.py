# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Url (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Url(Schema__Step__Base):                                    # Return current URL
    action              : Enum__Step__Action = Enum__Step__Action.GET_URL
