# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Screenshot__Request
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe

from sg_compute_specs.playwright.core.schemas.enums.Enum__Screenshot__Format                           import Enum__Screenshot__Format
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__JS__Expression              import Safe_Str__JS__Expression
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                    import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                import Safe_Str__Url__Permissive


class Schema__Screenshot__Request(Type_Safe):
    url         : Safe_Str__Url__Permissive = None                                  # None = stay on current page (steps mode only) — RFC-compliant (BUG-1)
    click       : Safe_Str__Selector      = None                                    # Element to click after load (e.g. cookie banner)
    javascript  : Safe_Str__JS__Expression = None                                   # JS to execute after load, before screenshot
    full_page   : bool                    = False
    format      : Enum__Screenshot__Format = Enum__Screenshot__Format.PNG
