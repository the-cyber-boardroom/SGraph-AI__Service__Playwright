# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Schema__Playwright__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe                                   import Type_Safe
from sg_compute_specs.playwright.schemas.Schema__Playwright__Info       import Schema__Playwright__Info


class Schema__Playwright__List(Type_Safe):
    region : str                          = ''
    stacks : List[Schema__Playwright__Info]
    total  : int                          = 0
