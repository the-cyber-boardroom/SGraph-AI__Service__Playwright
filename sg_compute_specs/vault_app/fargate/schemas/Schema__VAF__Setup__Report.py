# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Schema__VAF__Setup__Report
# Output envelope for a completed setup operation — phases + totals + status.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.collections.List__Schema__Phase__Result import List__Schema__Phase__Result


class Schema__VAF__Setup__Report(Type_Safe):
    cluster_name : str                       = ''
    operation    : str                       = ''             # 'check' / 'create' / 'update' / 'delete'
    phases       : List__Schema__Phase__Result = None
    total_ms     : int                       = 0
    ok           : bool                      = False
    error        : str                       = ''
