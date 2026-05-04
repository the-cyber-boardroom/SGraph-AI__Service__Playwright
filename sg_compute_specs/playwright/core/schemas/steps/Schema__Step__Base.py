# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Base (spec §5.6)
#
# Base class for every step in the declarative meta-language.
# The `action` field is the discriminator — each subclass MUST set a default
# matching its Enum__Step__Action variant.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Step_Id                            import Step_Id
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Timeout_MS                  import Safe_UInt__Timeout_MS


class Schema__Step__Base(Type_Safe):                                                # Fields common to every step
    action              : Enum__Step__Action                                        # Discriminator — MUST be set by each subclass
    id                  : Step_Id = None                                            # Caller-supplied; defaults to step index
    continue_on_error   : bool    = False                                           # Per-step halt override
    timeout_ms          : Safe_UInt__Timeout_MS = 30_000
