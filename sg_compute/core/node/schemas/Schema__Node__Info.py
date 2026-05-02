# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__Info
# Current state of one ephemeral compute node.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State


class Schema__Node__Info(Type_Safe):
    node_id       : str                 = ''
    spec_id       : str                 = ''
    region        : str                 = ''
    state         : Enum__Node__State   = Enum__Node__State.BOOTING
    public_ip     : str                 = ''
    private_ip    : str                 = ''
    instance_id   : str                 = ''
    instance_type : str                 = ''
    ami_id        : str                 = ''
    uptime_seconds: int                 = 0
