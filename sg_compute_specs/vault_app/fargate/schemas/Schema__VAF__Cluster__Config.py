# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Schema__VAF__Cluster__Config
# Resolved cluster config — populated from ECS cluster tags at start time.
# No disk persistence; describes what Tags__Reader extracts per Q3 decision.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__VAF__Cluster__Config(Type_Safe):
    cluster_name       : str = ''
    subnets            : str = ''                                                # comma-separated subnet IDs
    security_group     : str = ''
    dns_zone           : str = ''                                                # empty = no DNS
    execution_role_arn : str = ''
    task_role_arn      : str = ''                                                # empty = no task role
    log_group          : str = ''
    ecr_repo_name      : str = ''
    region             : str = ''
    created_at         : str = ''
