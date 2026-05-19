# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Schema__VAF__Timings__Record
# Historical timing record persisted per start to ~/.cache/sg/ as JSONL.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__VAF__Timings__Record(Type_Safe):
    slug           : str = ''
    cluster_name   : str = ''
    task_ready_ms  : int = 0
    vault_ready_ms : int = 0
    total_ms       : int = 0
    launch_type    : str = ''
    executed_at    : str = ''
