# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Browser Configuration Schemas (spec §5.2)
#
# `launch_args` behaviour: if the caller provides the list, it REPLACES the
# service defaults entirely (logged as a diagnostic). Callers who omit it get
# safe defaults for the deployment target.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                      import List

from osbot_utils.type_safe.Type_Safe                                                             import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str                                              import Safe_Str
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__User_Agent           import Safe_Str__Http__User_Agent
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                 import Safe_Str__Key
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                         import Safe_Str__Url
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Username                    import Safe_Str__Username

from sgraph_ai_service_playwright.schemas.enums.enums                                            import (
    Enum__Browser__Name                                                                          ,
    Enum__Browser__Provider                                                                      ,
)
from sgraph_ai_service_playwright.schemas.primitives.browser                                     import Safe_Str__Browser__Launch_Arg
from sgraph_ai_service_playwright.schemas.primitives.host                                        import Safe_Str__Host
from sgraph_ai_service_playwright.schemas.primitives.numeric                                     import Safe_UInt__Viewport_Dimension


class Schema__Proxy__Config(Type_Safe):                                             # Proxy settings — passed explicitly to chromium.launch()
    server              : Safe_Str__Url                                             # http://proxy.example.com:8080
    username            : Safe_Str__Username = None                                 # Optional basic auth
    password            : Safe_Str          = None                                  # Never logged
    bypass              : List[Safe_Str__Host]                                      # Domains to skip proxy for
    ignore_https_errors : bool = False                                              # True for TLS-intercepting proxies


class Schema__Viewport(Type_Safe):                                                  # Browser viewport dimensions
    width               : Safe_UInt__Viewport_Dimension = 1280
    height              : Safe_UInt__Viewport_Dimension = 800


class Schema__Browser__Config(Type_Safe):                                           # How to launch the browser
    provider            : Enum__Browser__Provider = Enum__Browser__Provider.LOCAL_SUBPROCESS
    browser_name        : Enum__Browser__Name     = Enum__Browser__Name.CHROMIUM
    headless            : bool                    = True
    launch_args         : List[Safe_Str__Browser__Launch_Arg]                       # Caller list replaces defaults entirely
    proxy               : Schema__Proxy__Config   = None
    viewport            : Schema__Viewport
    user_agent          : Safe_Str__Http__User_Agent = None                         # Override UA string
    locale              : Safe_Str__Key = "en-GB"                                   # Browser locale
    timezone            : Safe_Str__Key = None                                      # IANA timezone e.g. "Europe/London"
    cdp_endpoint_url    : Safe_Str__Url = None                                      # Required when provider=CDP_CONNECT
