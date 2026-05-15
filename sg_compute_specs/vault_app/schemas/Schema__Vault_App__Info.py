# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__Info
# State of one live vault-app EC2 instance.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vault_App__Info(Type_Safe):
    instance_id        : str  = ''
    stack_name         : str  = ''
    region             : str  = ''
    state              : str  = ''
    public_ip          : str  = ''
    private_ip         : str  = ''
    instance_type      : str  = ''
    ami_id             : str  = ''
    security_group_id  : str  = ''
    vault_url          : str  = ''    # https://<public-ip> (TLS on) or http://<public-ip>:8080 (plain)
    playwright_url     : str  = ''    # http://<public-ip>:11024 when --with-playwright; '' otherwise
    host_plane_url      : str = ''    # http://localhost:19009 — reachable only via the SSM port-forward below
    mitmweb_url         : str = ''    # http://localhost:19081/web/ — agent-mitmproxy's admin /web/* forwarder
    ssm_forward         : str = ''    # ready-to-paste `aws ssm start-session ...` for host-plane (:19009)
    mitmweb_ssm_forward : str = ''    # ready-to-paste `aws ssm start-session ...` for the mitmweb admin (:19081)
    tls_enabled        : bool = False # from StackTLS tag — drives the vault_url scheme
    access_token       : str  = ''    # from AccessToken tag — vault API key + access token (same value, two headers)
    with_playwright    : bool = False # from StackWithPlaywright tag
    container_engine   : str  = ''    # from StackEngine tag — docker | podman
    uptime_seconds     : int  = 0
    spot               : bool = False
    terminate_at       : str  = ''    # ISO-8601 UTC when auto-terminate fires; '' = no limit
    time_remaining_sec : int  = 0     # seconds until auto-terminate; 0 = no limit or expired
