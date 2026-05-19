# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/_shared — List__Str
# Typed list of plain strings used by aws/* report schemas (subnet IDs,
# rollback error messages, AZ names).
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List


class List__Str(Type_Safe__List):
    expected_type = str
