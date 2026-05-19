# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Schema__VAF__Start__Request
# Input contract for the fast-path start orchestrator.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__VAF__Start__Request(Type_Safe):
    cluster_name    : str  = ''      # resolved by Cluster__Resolver if empty
    slug            : str  = ''      # auto-generated if empty
    access_token    : str  = ''
    seed_vault_keys : str  = ''
    with_tls        : bool = True
    with_aws_dns    : bool = False
    public_ip       : bool = True    # assign public IP to task
    launch_type     : str  = 'FARGATE'
    cpu             : str  = ''      # uses spec default if empty
    memory          : str  = ''      # uses spec default if empty
    tags            : dict = None    # extra task tags (VaultApp__Slug added automatically)
    enable_exec     : bool = True    # enable ECS Exec (SSM) for shell access
    dns_zone        : str  = ''      # Route53 zone; when set, enables DNS upsert + TLS
