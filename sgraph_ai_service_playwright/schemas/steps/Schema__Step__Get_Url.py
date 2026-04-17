# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Url (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Url(Schema__Step__Base):                                    # Return current URL
    action              : Enum__Step__Action = Enum__Step__Action.GET_URL
