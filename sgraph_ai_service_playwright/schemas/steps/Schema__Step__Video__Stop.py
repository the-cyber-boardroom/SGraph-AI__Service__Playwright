# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Video__Stop (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Name                   import Safe_Str__File__Name

from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Video__Stop(Schema__Step__Base):                                # End video recording
    action              : Enum__Step__Action   = Enum__Step__Action.VIDEO_STOP
    save_as             : Safe_Str__File__Name = None
