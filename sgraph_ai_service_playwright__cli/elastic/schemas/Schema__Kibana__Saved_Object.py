# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Kibana__Saved_Object
# One row from /api/saved_objects/_find — minimal fields the CLI renders in
# `sp elastic dashboard list` and `sp elastic data-view list`. Kibana returns
# many more attributes per object (references, namespaces, version, score, …)
# but we only need id/type/title/updated_at for a useful `list` table.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text


class Schema__Kibana__Saved_Object(Type_Safe):
    id         : Safe_Str__Text
    type       : Safe_Str__Text
    title      : Safe_Str__Text
    updated_at : Safe_Str__Text                                                     # ISO-8601, Kibana-emitted; preserved as text rather than parsed
