# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Dispatch_Event (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Dict

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                    import Safe_Str__Key

from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Dispatch_Event(Schema__Step__Base):                             # Synthetic DOM event
    action              : Enum__Step__Action = Enum__Step__Action.DISPATCH_EVENT
    selector            : Safe_Str__Selector
    event_type          : Safe_Str__Key                                             # e.g. "click", "input"
    event_init          : Dict[Safe_Str__Key, Safe_Str__Text] = None
