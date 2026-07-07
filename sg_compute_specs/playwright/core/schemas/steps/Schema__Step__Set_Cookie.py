# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Set_Cookie
#
# Sets a cookie on the per-request BrowserContext. STATELESS by design: every
# request gets a fresh Playwright + browser + context (Browser__Launcher per-call
# lifecycle), the cookie is added to THAT context only, and the context is torn
# down when the request completes. No session persistence, no context reuse —
# a "reload" that shows the cookie in effect is simply a second navigate step in
# the SAME request.
#
# Playwright add_cookies contract: a cookie needs EITHER `url` OR `domain`+`path`
# (path defaults to '/' when only domain is given). Exactly-one-of url/domain is
# enforced in Request__Validator (rule 18 — all cross-schema validation there).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt                                                    import Safe_UInt

from sg_compute_specs.playwright.core.schemas.enums.Enum__Cookie__Same_Site                             import Enum__Cookie__Same_Site
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Cookie__Domain               import Safe_Str__Cookie__Domain
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Cookie__Name                 import Safe_Str__Cookie__Name
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Cookie__Path                 import Safe_Str__Cookie__Path
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Cookie__Value                import Safe_Str__Cookie__Value
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                 import Safe_Str__Url__Permissive
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Set_Cookie(Schema__Step__Base):                                 # Set cookie on the per-request context
    action              : Enum__Step__Action = Enum__Step__Action.SET_COOKIE
    name                : Safe_Str__Cookie__Name                                    # Required (non-empty enforced by Request__Validator)
    value               : Safe_Str__Cookie__Value                                   # Required; never echoed back in step results
    url                 : Safe_Str__Url__Permissive = None                          # URL form — Playwright derives domain + path from it
    domain              : Safe_Str__Cookie__Domain  = None                          # Domain form — pairs with `path` (defaults to '/')
    path                : Safe_Str__Cookie__Path    = None                          # Only meaningful with `domain`; Credentials__Loader defaults it to '/'
    secure              : bool = False
    http_only           : bool = False                                              # HttpOnly cookies are invisible to document.cookie (JS) — server-only
    same_site           : Enum__Cookie__Same_Site = None                            # Serialised as its capitalised value ("Strict"/"Lax"/"None")
    expires             : Safe_UInt = None                                          # Epoch seconds; omitted → session cookie (moot here — the context dies with the request anyway)
