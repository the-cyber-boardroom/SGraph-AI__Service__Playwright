# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Sequence__Config (spec §5.8)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Timeout_MS                  import Safe_UInt__Timeout_MS


class Schema__Sequence__Config(Type_Safe):                                          # Sequence-level config
    halt_on_error           : bool                   = True                         # Stop on first failure
    default_step_timeout_ms : Safe_UInt__Timeout_MS  = 30_000
    total_timeout_ms        : Safe_UInt__Timeout_MS  = 300_000                      # Whole-sequence budget
