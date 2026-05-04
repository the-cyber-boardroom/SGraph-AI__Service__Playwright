# ═══════════════════════════════════════════════════════════════════════════════
# Schema__Agentic__Health — GET /admin/health response (v0.1.29)
#
# Always 200. Reports whether the user app loaded cleanly ("loaded") or the
# boot shim caught a critical error and is serving the admin surface from the
# baked image in degraded mode ("degraded"). Carries the resolved code_source
# so operators can tell at a glance whether a Lambda is running the zipped
# version they expect or is falling back to passthrough / local.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                    import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous         import Safe_Str__Text__Dangerous


class Schema__Agentic__Health(Type_Safe):
    status      : Safe_Str__Text                                                    # 'loaded' when the user app imported cleanly; 'degraded' when the boot shim is the only thing running
    code_source : Safe_Str__Text__Dangerous                                         # Provenance string written by the boot shim — 's3:<bucket>/<key>…', 'local:<path>', 'passthrough:sys.path'. Dangerous variant preserves '/' and ':'.
