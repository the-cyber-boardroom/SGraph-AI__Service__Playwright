# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Plugin__Capability
# Ordered list of Enum__Plugin__Capability values for a plugin manifest entry.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability import Enum__Plugin__Capability


class List__Plugin__Capability(Type_Safe__List):
    expected_type = Enum__Plugin__Capability
