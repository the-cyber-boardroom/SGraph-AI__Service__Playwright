# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Screenshot__Batch__Response
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                        import List

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe

from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds               import Safe_UInt__Milliseconds
from sg_compute_specs.playwright.core.schemas.screenshot.Schema__Screenshot__Response                  import Schema__Screenshot__Response


class Schema__Screenshot__Batch__Response(Type_Safe):
    screenshots : List[Schema__Screenshot__Response]
    duration_ms : Safe_UInt__Milliseconds            = Safe_UInt__Milliseconds(0)
