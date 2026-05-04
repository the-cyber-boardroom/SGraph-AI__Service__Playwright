# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Service__Capabilities (spec §5.1)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Name                                 import Enum__Browser__Name
from sg_compute_specs.playwright.core.schemas.enums.Enum__Artefact__Sink                                import Enum__Artefact__Sink
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Memory_MB                   import Safe_UInt__Memory_MB
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Session_Lifetime_MS         import Safe_UInt__Session_Lifetime_MS


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
