# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Open_Design__Info
# State of one live Open Design EC2 instance.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Open_Design__Info(Type_Safe):
    instance_id       : str  = ''
    stack_name        : str  = ''
    region            : str  = ''
    state             : str  = ''
    public_ip         : str  = ''
    private_ip        : str  = ''
    instance_type     : str  = ''
    ami_id            : str  = ''
    security_group_id : str  = ''
    caller_ip         : str  = ''
    viewer_url        : str  = ''       # https://<public_ip>/
    has_ollama        : bool = False    # True when OLLAMA_BASE_URL tag is set
    uptime_seconds    : int  = 0
