# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Schema__Local__Edge__Usecase_Step
# One step in a scripted use-case run (label + pass/fail + detail). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Local__Edge__Usecase_Step(Type_Safe):
    label  : str
    ok     : bool = True
    detail : str
