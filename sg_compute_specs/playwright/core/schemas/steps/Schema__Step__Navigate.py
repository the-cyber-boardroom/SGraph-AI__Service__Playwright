# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Navigate (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Wait__State                                   import Enum__Wait__State
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                 import Safe_Str__Url__Permissive
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Navigate(Schema__Step__Base):                                   # Go to URL
    action              : Enum__Step__Action = Enum__Step__Action.NAVIGATE
    url                 : Safe_Str__Url__Permissive                                 # RFC-compliant URL — accepts ':' in fragment (vault keys etc.); BUG-1 (05-30 debrief response pack)
    wait_until          : Enum__Wait__State = Enum__Wait__State.LOAD
    referer             : Safe_Str__Url__Permissive = None
