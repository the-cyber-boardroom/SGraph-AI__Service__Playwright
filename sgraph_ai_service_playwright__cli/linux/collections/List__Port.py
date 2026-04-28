# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Port (linux)
# Ordered list of TCP port numbers for extra SG ingress rules. Pure type def.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List


class List__Port(Type_Safe__List):
    expected_type = int
