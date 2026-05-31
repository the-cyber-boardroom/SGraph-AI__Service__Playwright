# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Text (Φ3 — FR-2)
#
# Visible text of the page (or a selector subtree). Uses innerText, which
# respects CSS visibility — `display:none` and similar are excluded. The
# lightweight cousin of `get_content` (which can also return text but is
# heavier-weight and content-format-aware).
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Text(Schema__Step__Base):                                   # innerText of selector or page
    action              : Enum__Step__Action = Enum__Step__Action.GET_TEXT
    selector            : Safe_Str__Selector = None                                 # None → whole document body
    inline_in_response  : bool               = True                                 # Embed in result.text; otherwise sink via capture_config.page_content
