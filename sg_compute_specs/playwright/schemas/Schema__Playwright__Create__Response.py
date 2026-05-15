# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Schema__Playwright__Create__Response
# api_key is returned once here — it is not recoverable later.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                   import Type_Safe
from sg_compute_specs.playwright.schemas.Schema__Playwright__Info       import Schema__Playwright__Info


class Schema__Playwright__Create__Response(Type_Safe):
    stack_info : Schema__Playwright__Info = None
    api_key    : str = ''    # FAST_API__AUTH__API_KEY__VALUE — surfaced once on create, never again
    message    : str = ''
    elapsed_ms : int = 0
