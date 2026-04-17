# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Service__Info (spec §5.1 — GET /info response)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                 import Safe_Str__Version
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Display_Name       import Safe_Str__Display_Name

from sgraph_ai_service_playwright.schemas.enums.Enum__Deployment__Target                        import Enum__Deployment__Target
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities                 import Schema__Service__Capabilities


class Schema__Service__Info(Type_Safe):                                             # GET /info response
    service_name       : Safe_Str__Display_Name                                     # "sg-playwright"
    service_version    : Safe_Str__Version                                          # Service code version (from S3 zip)
    image_version      : Safe_Str__Version                                          # Container image version
    playwright_version : Safe_Str__Version                                          # Playwright library version
    chromium_version   : Safe_Str__Version                                          # Bundled Chromium version
    deployment_target  : Enum__Deployment__Target
    capabilities       : Schema__Service__Capabilities
