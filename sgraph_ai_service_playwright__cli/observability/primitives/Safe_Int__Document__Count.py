# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Int__Document__Count
# OpenSearch document count. -1 is a sentinel used by the legacy CLI to mean
# "not queried / query failed"; kept for parity until callers migrate to None.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int                                 import Safe_Int


class Safe_Int__Document__Count(Safe_Int):
    min_value = -1
    max_value = 2**63 - 1
