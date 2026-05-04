# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Config (spec §5.2)
#
# `launch_args` behaviour: if the caller provides the list, it REPLACES the
# service defaults entirely (logged as a diagnostic). Callers who omit it get
# safe defaults for the deployment target.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                          import List

from osbot_utils.type_safe.Type_Safe                                                                 import Type_Safe
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__User_Agent               import Safe_Str__Http__User_Agent
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                     import Safe_Str__Key
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                             import Safe_Str__Url

from sg_compute_specs.playwright.core.schemas.browser.Schema__Viewport                                   import Schema__Viewport
from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Name                                  import Enum__Browser__Name
from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Provider                              import Enum__Browser__Provider
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Browser__Launch_Arg           import Safe_Str__Browser__Launch_Arg


class Schema__Browser__Config(Type_Safe):                                           # How to launch the browser
    provider         : Enum__Browser__Provider = Enum__Browser__Provider.LOCAL_SUBPROCESS
    browser_name     : Enum__Browser__Name     = Enum__Browser__Name.CHROMIUM
    headless         : bool                    = True
    launch_args      : List[Safe_Str__Browser__Launch_Arg]                          # Caller list replaces defaults entirely
    viewport         : Schema__Viewport
    user_agent       : Safe_Str__Http__User_Agent = None                            # Override UA string
    locale           : Safe_Str__Key = "en-GB"                                      # Browser locale
    timezone         : Safe_Str__Key = None                                         # IANA timezone e.g. "Europe/London"
    cdp_endpoint_url : Safe_Str__Url = None                                         # Required when provider=CDP_CONNECT
