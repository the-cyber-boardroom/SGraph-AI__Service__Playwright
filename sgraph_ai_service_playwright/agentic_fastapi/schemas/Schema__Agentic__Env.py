# ═══════════════════════════════════════════════════════════════════════════════
# Schema__Agentic__Env — GET /admin/env response (v0.1.29)
#
# Redacted view of the environment. Surfaces ONLY the AGENTIC_* prefix so AWS
# secrets, API keys, and the app's own SG_PLAYWRIGHT__* auth vars can never
# leak through this endpoint. Per the v0.1.29 plan §5: "No AWS creds."
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                     import Dict

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                    import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous         import Safe_Str__Text__Dangerous


class Schema__Agentic__Env(Type_Safe):
    agentic_vars : Dict[Safe_Str__Text, Safe_Str__Text__Dangerous]                  # Only AGENTIC_* entries — AWS_* and SG_PLAYWRIGHT__* are excluded at the route layer. Values use Dangerous variant so '/' in paths is preserved.
