# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Screenshot (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Name                   import Safe_Str__File__Name

from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Screenshot(Schema__Step__Base):                                 # Capture screenshot
    action              : Enum__Step__Action   = Enum__Step__Action.SCREENSHOT
    full_page           : bool                 = False
    selector            : Safe_Str__Selector   = None                               # Element screenshot if provided
    save_as             : Safe_Str__File__Name = None                               # Filename within sink's folder/prefix
