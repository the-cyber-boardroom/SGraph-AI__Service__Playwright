# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Html (Φ3 — FR-2)
#
# outerHTML of the page (or a selector subtree). Distinct from `get_content`
# in two ways:
#   1. outerHTML (includes the element's own opening/closing tags) vs
#      innerHTML (children only).
#   2. Always-HTML — no content_format toggle.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Html(Schema__Step__Base):                                   # outerHTML of selector or whole document
    action              : Enum__Step__Action = Enum__Step__Action.GET_HTML
    selector            : Safe_Str__Selector = None                                 # None → page.content() (full document)
    inline_in_response  : bool               = True                                 # Embed in result.html; otherwise sink via capture_config.page_content
