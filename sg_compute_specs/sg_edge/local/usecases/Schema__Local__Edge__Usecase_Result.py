# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Schema__Local__Edge__Usecase_Result
# Outcome of one scripted use-case: id, name, ordered steps, overall pass/fail.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sg_compute_specs.sg_edge.local.usecases.List__Local__Edge__Usecase_Step    import List__Local__Edge__Usecase_Step


class Schema__Local__Edge__Usecase_Result(Type_Safe):
    id     : str
    name   : str
    steps  : List__Local__Edge__Usecase_Step
    passed : bool = True
