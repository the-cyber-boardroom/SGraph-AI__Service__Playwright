# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: List__Schema__Vnc__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sg_compute_specs.vnc.schemas.Schema__Vnc__Stack__Info                          import Schema__Vnc__Stack__Info


class List__Schema__Vnc__Stack__Info(Type_Safe__List):
    expected_type = Schema__Vnc__Stack__Info
