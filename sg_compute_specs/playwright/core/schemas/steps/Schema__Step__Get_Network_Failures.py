# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Network_Failures (Φ4)
#
# Returns all buffered page.on('requestfailed') events. Failed requests are
# usually the most diagnostic load-time signal — they tell you which
# resource the page couldn't fetch (CORS, blocked, 404, DNS, etc.). The
# probe-batch (Φ5) bundles this into the per-probe diagnostics.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Network_Failures(Schema__Step__Base):                       # Buffered requestfailed events
    action              : Enum__Step__Action = Enum__Step__Action.GET_NETWORK_FAILURES
