# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_A11y_Tree (Φ3 — FR-5b)
#
# Accessibility tree snapshot. Built by Playwright via page.accessibility.
# snapshot() and returned inline as a JSON object. The a11y view often
# resolves "what does this control DO" faster than the DOM tree because
# it's normalised to ARIA roles + accessible names.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_A11y_Tree(Schema__Step__Base):                              # page.accessibility.snapshot → JSON
    action              : Enum__Step__Action = Enum__Step__Action.GET_A11Y_TREE
    root_selector       : Safe_Str__Selector = None                                 # None → whole document; else scoped to that element
    interesting_only    : bool               = True                                 # Playwright default — prunes nodes that don't change semantics
