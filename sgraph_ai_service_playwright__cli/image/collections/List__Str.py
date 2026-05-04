# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Str
# Typed list of plain strings used by image-build schemas (image tags,
# ignore-name patterns). Lives under cli/image/ because it's the only
# section that needs a generic List__Str today; promote to a shared
# location if other sections start needing the same shape.
# Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List


class List__Str(Type_Safe__List):
    expected_type = str
