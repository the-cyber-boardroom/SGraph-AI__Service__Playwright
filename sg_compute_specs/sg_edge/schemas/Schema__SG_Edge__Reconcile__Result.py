# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Schema__SG_Edge__Reconcile__Result
# Outcome of one SG_Edge__Fleet__Reconciler.reconcile() pass: the proxy count
# before the pass, the desired target, and the instance ids launched to converge
# toward it (scale-UP only — scale-DOWN is idle_check's job). Returned by the
# /__edge__/reconcile route via .json(). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                  import Type_Safe

from sg_compute_specs.sg_edge.schemas.List__SG_Edge__Instance_Id      import List__SG_Edge__Instance_Id


class Schema__SG_Edge__Reconcile__Result(Type_Safe):
    current  : int                          = 0                                  # proxies in DNS before this pass
    target   : int                          = 0                                  # desired proxy count
    launched : List__SG_Edge__Instance_Id                                        # instance ids launched this pass
