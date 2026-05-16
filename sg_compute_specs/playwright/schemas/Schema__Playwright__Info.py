# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Schema__Playwright__Info
# State of one live playwright EC2 instance.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Playwright__Info(Type_Safe):
    instance_id        : str  = ''
    stack_name         : str  = ''
    region             : str  = ''
    state              : str  = ''
    public_ip          : str  = ''
    private_ip         : str  = ''
    instance_type      : str  = ''
    ami_id             : str  = ''
    security_group_id  : str  = ''
    playwright_url     : str  = ''    # http://<public-ip>:8000 — the Playwright FastAPI
    sidecar_admin_url  : str  = ''    # http://<public-ip>:8001 — agent-mitmproxy admin API (only with_mitmproxy)
    with_mitmproxy     : bool = False # from StackWithMitmproxy tag
    api_key            : str  = ''    # from StackApiKey tag — FAST_API__AUTH__API_KEY__VALUE; same value for the X-API-Key header AND the X-API-Key cookie. Visible to anyone with ec2:DescribeInstances.
    uptime_seconds     : int  = 0
    spot               : bool = False
    terminate_at       : str  = ''    # ISO-8601 UTC when auto-terminate fires; '' = no limit
    time_remaining_sec : int  = 0     # seconds until auto-terminate; 0 = no limit or expired
