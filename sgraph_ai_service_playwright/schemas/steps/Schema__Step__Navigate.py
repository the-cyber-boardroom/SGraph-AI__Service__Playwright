# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Navigate (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.enums.Enum__Wait__State                                   import Enum__Wait__State
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Navigate(Schema__Step__Base):                                   # Go to URL
    action              : Enum__Step__Action = Enum__Step__Action.NAVIGATE
    url                 : Safe_Str__Url
    wait_until          : Enum__Wait__State = Enum__Wait__State.LOAD
    referer             : Safe_Str__Url = None
