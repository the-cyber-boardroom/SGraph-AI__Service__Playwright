# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Wait (FR-4)
#
# The plain "sleep for N ms" step. Distinct from `wait_for` which waits on a
# condition: this one is the explicit, intentional pause for the cases where
# a deterministic delay actually IS the right answer (e.g. throttling a
# scripted sequence to avoid rate limits). Caps reuse Safe_UInt__Timeout_MS
# so a step cannot block the whole sequence past the global timeout budget.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Timeout_MS                  import Safe_UInt__Timeout_MS
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Wait(Schema__Step__Base):                                       # Fixed-duration pause
    action      : Enum__Step__Action     = Enum__Step__Action.WAIT
    duration_ms : Safe_UInt__Timeout_MS  = 0                                        # How long to sleep — 0 = no-op; explicit so the wire payload is self-documenting
