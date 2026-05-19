# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Schema__VAF__Setup__Request
# Input parameters for Vault_App__Fargate__Setup operations.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__VAF__Setup__Request(Type_Safe):
    cluster_name        : str  = ''                           # auto-generated if empty
    ecr_repo_name       : str  = ''                           # from spec if empty
    subnets             : str  = ''                           # comma-separated; required for CLUSTER phase
    security_group      : str  = ''                           # required for CLUSTER phase
    execution_role_name : str  = 'vault-app-fargate-execution'
    task_role_name      : str  = ''                           # optional
    log_group           : str  = ''                           # from spec.default_log_group if empty
    dns_zone            : str  = ''                           # optional
    region              : str  = ''                           # from boto3 session if empty
    source_image        : str  = 'diniscruz/sg-send-vault:latest'
    cpu                 : str  = '512'
    memory              : str  = '1024'
    phases              : list = None                         # list of Enum__VAF__Setup__Phase; None = all
    continue_on_error   : bool = False
    dry_run             : bool = False
