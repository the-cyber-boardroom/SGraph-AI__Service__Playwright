# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Plugin__Manifest
# Response for GET /catalog/manifest — the full typed plugin registry.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe

from sgraph_ai_service_playwright__cli.core.plugin.collections.List__Schema__Plugin__Manifest__Entry import List__Schema__Plugin__Manifest__Entry


class Schema__Plugin__Manifest(Type_Safe):
    schema_version : int                              = 1    # bump when shape changes incompatibly
    plugins        : List__Schema__Plugin__Manifest__Entry
