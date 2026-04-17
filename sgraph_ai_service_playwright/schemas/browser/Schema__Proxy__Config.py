# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Proxy__Config (spec §5.2)
#
# Nested `auth` rather than flat username/password at the top level is
# deliberate — callers need to know the creds take a different code path than
# `server` / `bypass`. See Schema__Proxy__Auth__Basic for why.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                    import List

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                       import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Auth__Basic                   import Schema__Proxy__Auth__Basic
from sgraph_ai_service_playwright.schemas.primitives.host.Safe_Str__Host                       import Safe_Str__Host


class Schema__Proxy__Config(Type_Safe):                                             # Proxy settings — server/bypass go to chromium.launch(); auth goes via CDP Fetch
    server              : Safe_Str__Url                                             # http://proxy.example.com:8080
    bypass              : List[Safe_Str__Host]                                      # Domains to skip proxy for
    ignore_https_errors : bool                      = False                         # Applied to new_context() for TLS-intercepting proxies (mitmproxy et al)
    auth                : Schema__Proxy__Auth__Basic = None                         # None = open proxy, no auth. Populated = CDP Fetch handlers registered on each page.
