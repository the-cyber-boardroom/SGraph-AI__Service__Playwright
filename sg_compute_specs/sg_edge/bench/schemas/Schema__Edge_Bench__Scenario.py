# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Schema__Edge_Bench__Scenario
# Descriptor for one bench scenario from the doc-05 catalog: its id (P-01, F-01,
# X-12, …), human name, tier, and the target it runs against. Pure data — no
# methods; the run logic + thresholds live in the scenario registry.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                  import Type_Safe

from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Tier      import Enum__Edge_Bench__Tier
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Target    import Enum__Edge_Bench__Target


class Schema__Edge_Bench__Scenario(Type_Safe):
    id     : str                                                                     # doc-05 id, e.g. 'F-01'
    name   : str                                                                     # e.g. 'edge_cold_cold_boot'
    tier   : Enum__Edge_Bench__Tier   = Enum__Edge_Bench__Tier.PRIMITIVE
    target : Enum__Edge_Bench__Target = Enum__Edge_Bench__Target.LOCAL
    doc    : str                                                                     # one-line description of what the local variant measures
