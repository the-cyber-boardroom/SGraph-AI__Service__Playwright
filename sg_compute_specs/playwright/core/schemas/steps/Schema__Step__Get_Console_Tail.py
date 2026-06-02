# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Console_Tail (Φ4)
#
# Returns the last N buffered console events from the page listener buffer.
# The buffer is wired by Sequence__Runner BEFORE the first navigate so
# load-time messages are captured (page.on('console') misses anything that
# fired before the listener was attached). Architected here for the
# probe-batch (Φ5) which composes this verb into the diagnostic bundle.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Console_Tail(Schema__Step__Base):                           # Last N console events
    action              : Enum__Step__Action = Enum__Step__Action.GET_CONSOLE_TAIL
    lines               : Safe_UInt          = 100                                  # How many trailing events to return; capped by buffer's own ring-buffer limit
