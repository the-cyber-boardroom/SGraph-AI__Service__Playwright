# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Schema__Vscode__Info
# State of one live vscode EC2 instance.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vscode__Info(Type_Safe):
    instance_id        : str  = ''
    stack_name         : str  = ''
    region             : str  = ''
    state              : str  = ''
    public_ip          : str  = ''
    private_ip         : str  = ''
    instance_type      : str  = ''
    ami_id             : str  = ''
    security_group_id  : str  = ''
    distribution       : str  = ''    # from StackDistribution tag
    ingress            : str  = ''    # from StackIngress tag
    vscode_url         : str  = ''    # http://localhost:<port> (SSM) or https://<host> (public)
    ssm_forward        : str  = ''    # ready-to-paste AWS-StartPortForwardingSession command
    ssm_session        : str  = ''    # ready-to-paste interactive SSM shell command
    disk_size_gb       : int  = 0
    uptime_seconds     : int  = 0
    spot               : bool = False
    terminate_at       : str  = ''    # ISO-8601 UTC when auto-terminate fires; '' = no limit
    time_remaining_sec : int  = 0     # seconds until auto-terminate; 0 = no limit or expired
