# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Proxy__Config (spec §5.2)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                    import List

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str                                            import Safe_Str
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                       import Safe_Str__Url
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Username                  import Safe_Str__Username

from sgraph_ai_service_playwright.schemas.primitives.host.Safe_Str__Host                       import Safe_Str__Host


class Schema__Proxy__Config(Type_Safe):                                             # Proxy settings — passed explicitly to chromium.launch()
    server              : Safe_Str__Url                                             # http://proxy.example.com:8080
    username            : Safe_Str__Username = None                                 # Optional basic auth
    password            : Safe_Str          = None                                  # Never logged
    bypass              : List[Safe_Str__Host]                                      # Domains to skip proxy for
    ignore_https_errors : bool = False                                              # True for TLS-intercepting proxies
