# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Pdf (Φ3 — FR-5d)
#
# Renders the page to PDF via page.pdf(). The bytes are routed through
# capture_config.pdf (sink + Artefact__Writer.capture_pdf), so the step
# result carries a Schema__Artefact__Ref pointer rather than inline base64
# (PDFs are routinely large enough to blow the 20 MB inline cap).
#
# print options are kept narrow on purpose — Playwright supports ~30 PDF
# knobs; expose the ones that actually change layout. Add more behind feature
# requests rather than upfront.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Str                                                 import Safe_Str

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Pdf(Schema__Step__Base):                                    # page.pdf() → PDF artefact
    action              : Enum__Step__Action = Enum__Step__Action.GET_PDF
    format              : Safe_Str           = 'A4'                                 # 'A4' | 'Letter' | 'Legal' | …; Playwright passes through to Chromium
    landscape           : bool               = False
    print_background    : bool               = True                                 # Default-true; CSS backgrounds usually matter for archival captures
