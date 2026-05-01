# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Stack__Info
# Generic EC2 instance state shared by all stack mappers.
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
