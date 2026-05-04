# ═══════════════════════════════════════════════════════════════════════════════
# Schema__Agentic__Info — GET /admin/info response (v0.1.29)
#
# Framework-level introspection: app identity + resolved code provenance +
# image / Python versions. Distinct from /health/info (which is the app-specific
# surface with Playwright / Chromium versions and capabilities). Everything here
# is a facts-about-the-container answer — never reaches the app service layer.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                    import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous         import Safe_Str__Text__Dangerous
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                 import Safe_Str__Version


class Schema__Agentic__Info(Type_Safe):
    app_name       : Safe_Str__Text                                                 # AGENTIC_APP_NAME, e.g. 'sg-playwright'
    app_stage      : Safe_Str__Text                                                 # AGENTIC_APP_STAGE — 'dev' / 'main' / 'prod'
    app_version    : Safe_Str__Version                                              # AGENTIC_APP_VERSION — the loaded zip version
    image_version  : Safe_Str__Version                                              # AGENTIC_IMAGE_VERSION — the baked container image version
    code_source    : Safe_Str__Text__Dangerous                                      # 's3:…', 'local:…', or 'passthrough:sys.path' — needs '/' preserved
    python_version : Safe_Str__Text__Dangerous                                      # sys.version — full string for debuggability; preserves '()' and '.' chars
