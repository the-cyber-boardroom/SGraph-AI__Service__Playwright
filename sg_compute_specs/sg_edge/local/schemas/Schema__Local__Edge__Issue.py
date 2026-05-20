# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Schema__Local__Edge__Issue
# A single check finding (severity + area + message), surfaced by
# Local__Edge__Stack.check(). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Severity      import Enum__Local__Edge__Severity


class Schema__Local__Edge__Issue(Type_Safe):
    severity : Enum__Local__Edge__Severity = Enum__Local__Edge__Severity.INFO
    area     : str
    message  : str
