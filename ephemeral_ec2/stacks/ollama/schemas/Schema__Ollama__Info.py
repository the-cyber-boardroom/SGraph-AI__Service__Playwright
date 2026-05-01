# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Ollama__Info
# State of one live Ollama EC2 instance.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Ollama__Info(Type_Safe):
    instance_id       : str  = ''
    stack_name        : str  = ''
    region            : str  = ''
    state             : str  = ''
    public_ip         : str  = ''
    private_ip        : str  = ''
    instance_type     : str  = ''
    ami_id            : str  = ''
    security_group_id : str  = ''
    model_name        : str  = ''    # from StackModel tag
    api_base_url      : str  = ''    # http://{private_ip}:11434/v1
    uptime_seconds    : int  = 0
    gpu_count         : int  = 0
