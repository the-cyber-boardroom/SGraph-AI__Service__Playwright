# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Enum__SG_Edge__Fleet__State
# Conceptual proxy-fleet state (brief 02). The Edge Waker is convergent — there is
# NO lock and no persisted state machine; these labels describe the fleet's
# observed condition (derived from the count of proxies.<parent> A records), used
# for status reporting and the bench harness. Transitions are driven by
# reconciliation toward a target proxy count, not by a coordinator.
#
#   ZERO ──cold-cold trigger──> BOOTING ──health green + A record──> ACTIVE
#   ACTIVE ──reconcile up──> SCALING ──proxy added──> ACTIVE   (SCALING deferred to Phase 3)
#   ACTIVE ──idle teardown (zero_streak)──> DRAINING ──drain done──> ZERO
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__SG_Edge__Fleet__State(str, Enum):
    ZERO     = 'zero'                                                          # no proxies running — $0 baseline
    BOOTING  = 'booting'                                                       # EC2 launched, waiting for HTTP health
    ACTIVE   = 'active'                                                        # N>=1 proxies serving, in DNS
    SCALING  = 'scaling'                                                       # reconciling toward a higher target (Phase 3)
    DRAINING = 'draining'                                                      # removed from DNS, waiting connections to drain

    def __str__(self):
        return self.value
