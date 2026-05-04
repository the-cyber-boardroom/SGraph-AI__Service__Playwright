# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: List__Schema__Podman__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sg_compute_specs.podman.schemas.Schema__Podman__Info                           import Schema__Podman__Info


class List__Schema__Podman__Info(Type_Safe__List):
    expected_type = Schema__Podman__Info
