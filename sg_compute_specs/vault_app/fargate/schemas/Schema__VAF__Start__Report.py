# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Schema__VAF__Start__Report
# Output envelope for the fast-path start orchestrator.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.collections.List__Schema__Phase__Result import List__Schema__Phase__Result


class Schema__VAF__Start__Report(Type_Safe):
    slug            : str                        = ''
    cluster_name    : str                        = ''
    task_arn        : str                        = ''
    task_definition : str                        = ''
    public_ip       : str                        = ''
    private_ip      : str                        = ''
    vault_url       : str                        = ''
    access_token    : str                        = ''
    phases          : List__Schema__Phase__Result = None
    task_ready_ms   : int                        = 0    # cumulative through WAIT_RUNNING
    vault_ready_ms  : int                        = 0    # cumulative through WAIT_HEALTH
    total_ms        : int                        = 0
    ok              : bool                       = False
    error           : str                        = ''
    executed_at     : str                        = ''   # ISO-8601 UTC
