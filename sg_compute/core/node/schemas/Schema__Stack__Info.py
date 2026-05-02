# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Stack__Info
# Legacy EC2 instance state shared by all spec mappers.
# Kept for backwards compatibility; new code should use Schema__Node__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Stack__Info(Type_Safe):
    instance_id       : str = ''
    stack_name        : str = ''
    stack_type        : str = ''
    region            : str = ''
    state             : str = ''
    public_ip         : str = ''
    private_ip        : str = ''
    instance_type     : str = ''
    ami_id            : str = ''
    security_group_id : str = ''
    uptime_seconds    : int = 0
