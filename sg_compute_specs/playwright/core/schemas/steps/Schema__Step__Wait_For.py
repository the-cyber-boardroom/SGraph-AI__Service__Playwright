# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Wait_For (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt                                                    import Safe_UInt
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                            import Safe_Str__Text

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Wait__State                                   import Enum__Wait__State
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__JS__Expression               import Safe_Str__JS__Expression
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                 import Safe_Str__Url__Permissive
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Wait_For(Schema__Step__Base):                                   # Wait for condition
    action              : Enum__Step__Action = Enum__Step__Action.WAIT_FOR
    selector            : Safe_Str__Selector        = None                          # Wait for selector (if provided)
    text                : Safe_Str__Text            = None                          # FR-1a — wait for visible page text (page.get_by_text); pairs with `selector` to scope the search
    url_pattern         : Safe_Str__Url__Permissive = None                          # Wait for URL match (RFC-compliant; accepts ':' in fragment — BUG-1)
    state               : Enum__Wait__State         = None                          # Wait for page state
    visible             : bool                      = True                          # For selector waits: visible vs attached
    selector_gone       : bool                      = False                         # FR-1b — wait for selector to detach from the DOM (state='detached'); overrides `visible` when True
    function            : Safe_Str__JS__Expression  = None                          # FR-1c — wait until a JS predicate returns truthy (page.wait_for_function); allowlist-gated, same gate as EVALUATE
    network_idle_ms     : Safe_UInt                 = None                          # FR-1d — wait until no in-flight requests for N consecutive ms (page.on('request')/('response') buffer); requires Sequence__Runner to have attached the listener buffer
