# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__Create__Request__Base
# Unified base for all per-spec node-creation requests.
# Per-spec schemas extend this and add spec-specific fields.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.enums.Enum__Stack__Creation_Mode                  import Enum__Stack__Creation_Mode


class Schema__Node__Create__Request__Base(Type_Safe):
    spec_id       : str                         = ''
    node_name     : str                         = ''    # auto-generated when empty
    region        : str                         = ''
    instance_type : str                         = 't3.large'
    ami_id        : str                         = ''    # empty = use latest AL2023
    caller_ip     : str                         = ''    # empty = auto-detected
    max_hours     : int                         = 1
    creation_mode : Enum__Stack__Creation_Mode  = Enum__Stack__Creation_Mode.FRESH
