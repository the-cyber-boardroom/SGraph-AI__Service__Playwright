# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Get_Dom_Tree (Φ3 — FR-2 headline verb)
#
# Compact JSON view of the DOM rooted at `root_selector` (or document.body).
# Each node carries the navigation essentials — tag/id/class/role/accessible_name
# /rect/visible/child_count — and recurses up to `max_depth`. Designed to answer
# "what selector should I be targeting?" without dumping the full HTML.
#
# Bounded by `max_depth` and `include_invisible` to keep payload size sane on
# SPA pages with deep React trees.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Get_Dom_Tree(Schema__Step__Base):                               # Compact JSON DOM
    action              : Enum__Step__Action = Enum__Step__Action.GET_DOM_TREE
    root_selector       : Safe_Str__Selector = None                                 # None → document.body
    max_depth           : Safe_UInt          = 8                                    # Tree recursion limit; deep React trees blow up payload without this
    include_invisible   : bool               = False                                # True → descend into display:none / opacity:0 nodes too
