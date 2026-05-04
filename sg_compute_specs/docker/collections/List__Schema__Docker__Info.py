# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: List__Schema__Docker__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sg_compute_specs.docker.schemas.Schema__Docker__Info                           import Schema__Docker__Info


class List__Schema__Docker__Info(Type_Safe__List):
    expected_type = Schema__Docker__Info
