# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Local_Claude__Info
# State of one live local-claude EC2 instance.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Local_Claude__Info(Type_Safe):
    instance_id       : str  = ''
    stack_name        : str  = ''
    region            : str  = ''
    state             : str  = ''
    public_ip         : str  = ''
    private_ip        : str  = ''
    instance_type     : str  = ''
    ami_id            : str  = ''
    security_group_id : str  = ''
    model_name        : str  = ''    # from StackModel tag — the HF model reference
    tool_parser       : str  = ''    # from StackToolParser tag
    disk_size_gb      : int  = 0
    uptime_seconds    : int  = 0
    gpu_count         : int  = 0
    spot              : bool = False
