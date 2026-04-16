# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Service Info and Health Schemas (spec §5.1)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                     import List

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                 import Safe_Str__Version
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                    import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                import Timestamp_Now
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Display_Name       import Safe_Str__Display_Name
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                import Safe_Str__Key

from sgraph_ai_service_playwright.schemas.enums.enums                                           import (
    Enum__Browser__Name                                                                         ,
    Enum__Artefact__Sink                                                                        ,
    Enum__Deployment__Target                                                                    ,
)
from sgraph_ai_service_playwright.schemas.primitives.numeric                                    import (
    Safe_UInt__Session_Lifetime_MS                                                              ,
    Safe_UInt__Memory_MB                                                                        ,
)


class Schema__Service__Capabilities(Type_Safe):                                     # What this deployment target CAN do
    max_session_lifetime_ms : Safe_UInt__Session_Lifetime_MS                        # E.g. 900_000 on Lambda
    supports_persistent     : bool                                                  # True for container; False for Lambda warm-only
    supports_video          : bool                                                  # Requires writable disk space
    available_browsers      : List[Enum__Browser__Name]                             # Typically just CHROMIUM on Lambda
    supported_sinks         : List[Enum__Artefact__Sink]                            # LOCAL_FILE excluded on Lambda
    memory_budget_mb        : Safe_UInt__Memory_MB                                  # Informational
    has_vault_access        : bool                                                  # Can reach SG/Send API
    has_s3_access           : bool                                                  # Can reach S3
    has_network_egress      : bool                                                  # False in some sandboxed envs
    proxy_configured        : bool                                                  # Egress routes through proxy


class Schema__Service__Info(Type_Safe):                                             # GET /info response
    service_name            : Safe_Str__Display_Name                                # "sg-playwright"
    service_version         : Safe_Str__Version                                     # Service code version (from S3 zip)
    image_version           : Safe_Str__Version                                     # Container image version
    playwright_version      : Safe_Str__Version                                     # Playwright library version
    chromium_version        : Safe_Str__Version                                     # Bundled Chromium version
    deployment_target       : Enum__Deployment__Target
    capabilities            : Schema__Service__Capabilities


class Schema__Health__Check(Type_Safe):                                             # Individual health dimension
    check_name              : Safe_Str__Key                                         # e.g. "chromium_process"
    healthy                 : bool
    detail                  : Safe_Str__Text                                        # Human-readable reason


class Schema__Health(Type_Safe):                                                    # GET /health response
    healthy                 : bool                                                  # Aggregate of all checks
    checks                  : List[Schema__Health__Check]
    timestamp               : Timestamp_Now
