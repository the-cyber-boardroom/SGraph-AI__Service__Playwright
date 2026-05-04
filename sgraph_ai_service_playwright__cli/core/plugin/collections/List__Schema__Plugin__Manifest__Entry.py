# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Plugin__Manifest__Entry
# Ordered list of manifest entries for Schema__Plugin__Manifest.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List                   import Type_Safe__List

from sgraph_ai_service_playwright__cli.core.plugin.schemas.Schema__Plugin__Manifest__Entry import Schema__Plugin__Manifest__Entry


class List__Schema__Plugin__Manifest__Entry(Type_Safe__List):
    expected_type = Schema__Plugin__Manifest__Entry
