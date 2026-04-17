# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Video__Start (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.enums.Enum__Video__Codec                                  import Enum__Video__Codec
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Video__Start(Schema__Step__Base):                               # Begin video recording
    action              : Enum__Step__Action = Enum__Step__Action.VIDEO_START
    codec               : Enum__Video__Codec = Enum__Video__Codec.WEBM
