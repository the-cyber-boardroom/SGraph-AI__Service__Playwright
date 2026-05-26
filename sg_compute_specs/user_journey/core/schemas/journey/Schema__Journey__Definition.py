# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Definition (one declarative user journey)
#
# Adopts the qa-vault-app Schema__QA__Scenario shape (renamed). `steps` is parsed
# by the substrate's Enum__Step__Action; `assertions` by the assertion registry.
# `browser_config` / `capture_config` reuse the substrate's published schemas.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                    import Safe_Str__Key
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Journey_Id                       import Journey_Id


class Schema__Journey__Definition(Type_Safe):                                       # One declarative user journey
    journey_id     : Journey_Id              = None                                 # Unique within the vault
    target_url     : Safe_Str__Url           = None                                 # Entry point
    environment    : Safe_Str__Key           = None                                 # 'dev' | 'main' | 'prod' — free-form
    browser_config : Schema__Browser__Config = None                                # Reused substrate schema; defaults applied
    capture_config : Schema__Capture__Config = None                                # Reused substrate schema; defaults applied
    steps          : List[dict]                                                     # Parsed by Enum__Step__Action
    assertions     : List[dict]                                                     # Parsed by the assertion registry
    tags           : List[Safe_Str__Key]
