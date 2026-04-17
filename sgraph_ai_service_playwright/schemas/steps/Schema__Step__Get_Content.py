# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Content (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright.schemas.enums.Enum__Content__Format                               import Enum__Content__Format
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Content(Schema__Step__Base):                                # Return HTML/text
    action              : Enum__Step__Action    = Enum__Step__Action.GET_CONTENT
    selector            : Safe_Str__Selector    = None                              # Element content, or full page if None
    content_format      : Enum__Content__Format = Enum__Content__Format.HTML
    inline_in_response  : bool                  = True                              # Embed in result; else route via capture_config
