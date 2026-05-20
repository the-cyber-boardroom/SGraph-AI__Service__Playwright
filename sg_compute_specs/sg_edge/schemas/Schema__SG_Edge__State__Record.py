# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Schema__SG_Edge__State__Record
# Typed form of the _state.<parent> TXT record — the ONLY piece of Edge Waker
# state, and it lives in DNS (brief 01/02: "There is no S3 lock"). Holds the
# idle-teardown counter. Wire form is key=value;key=value under the 255-char DNS
# TXT limit, e.g. "zero_streak=2;updated=1747700000".
#
# Fleet membership is NOT stored here — it is the set of proxies.<parent> A
# records (read directly from Route 53). The Edge Waker is convergent: it reads
# DNS ground truth and reconciles; no lock, no membership blob. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute_specs.sg_edge.primitives.Safe_Int__SG_Edge__Cycle_Count      import Safe_Int__SG_Edge__Cycle_Count
from sg_compute_specs.sg_edge.primitives.Safe_Int__SG_Edge__Unix_Ts          import Safe_Int__SG_Edge__Unix_Ts


class Schema__SG_Edge__State__Record(Type_Safe):
    zero_streak : Safe_Int__SG_Edge__Cycle_Count = Safe_Int__SG_Edge__Cycle_Count()  # consecutive idle-checks at zero vaults
    updated     : Safe_Int__SG_Edge__Unix_Ts     = Safe_Int__SG_Edge__Unix_Ts()      # unix ts of last counter write
