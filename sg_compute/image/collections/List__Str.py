# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — List__Str
# Typed list of plain strings (image tags, ignore-name patterns). Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List


class List__Str(Type_Safe__List):
    expected_type = str
