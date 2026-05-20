# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Schema__SG_Edge__Idle__Result
# Outcome of one SG_Edge__Fleet__Reconciler.idle_check() pass: how many vault
# slugs were active, the resulting zero_streak counter, the action taken, and (on
# teardown) the proxy IPs drained. Returned by the /__edge__/idle-check route via
# .json(). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                  import Type_Safe

from sg_compute_specs.sg_edge.enums.Enum__SG_Edge__Idle__Action       import Enum__SG_Edge__Idle__Action
from sg_compute_specs.sg_edge.schemas.List__SG_Edge__IP               import List__SG_Edge__IP


class Schema__SG_Edge__Idle__Result(Type_Safe):
    active      : int                       = 0                                  # active vault slugs observed
    zero_streak : int                       = 0                                  # consecutive idle checks after this pass
    action      : Enum__SG_Edge__Idle__Action = Enum__SG_Edge__Idle__Action.INCREMENT
    drained     : List__SG_Edge__IP                                              # proxy ips terminated (teardown only)
