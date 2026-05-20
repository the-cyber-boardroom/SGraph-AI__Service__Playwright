# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Safe_Int__Edge_Bench__Millis
# A duration / threshold expressed in whole milliseconds. The bench works in
# integer ms throughout (acceptance thresholds in doc 05 are sub-second) — no
# floats, debuggable straight from the JSON report.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Edge_Bench__Millis(Safe_Int):
    min_value = 0
