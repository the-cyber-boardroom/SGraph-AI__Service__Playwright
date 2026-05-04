# ═══════════════════════════════════════════════════════════════════════════════
# Schema__Agentic__Manifest — GET /admin/manifest response (v0.1.29)
#
# Single self-describing entry point. Points at:
#   • the OpenAPI doc (for machine-readable route enumeration),
#   • the capabilities stub (for declared axioms / narrowing),
#   • the available SKILL files (keyed by audience: human / browser / agent).
#
# An LLM agent should be able to read ONE response and know where to go next.
# Paths are URL paths (relative to the Function URL / base), not absolute URLs
# — the client supplies the host.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                     import Dict

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                    import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url__Path                  import Safe_Str__Url__Path


class Schema__Agentic__Manifest(Type_Safe):
    app_name         : Safe_Str__Text                                               # Convenience echo of /admin/info → app_name
    openapi_path     : Safe_Str__Url__Path                                          # Path to the OpenAPI JSON, e.g. '/openapi.json'
    capabilities_path: Safe_Str__Url__Path                                          # Path to the capabilities.json surface, e.g. '/admin/capabilities'
    skills           : Dict[Safe_Str__Text, Safe_Str__Url__Path]                    # audience -> '/admin/skills/{audience}'
