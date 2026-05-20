# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — edge: Enum__Edge__Fleet__State
# The proxy-fleet state machine (brief 02). Transitions are driven by the Edge
# Waker and serialised by the S3 boot lock during zero -> booting -> active:
#
#   ZERO ──cold-cold trigger + lock──> BOOTING ──health green + DNS A──> ACTIVE
#   ACTIVE ──scale-up──> SCALING ──proxy added──> ACTIVE
#   ACTIVE ──idle teardown──> DRAINING ──drain complete──> ZERO
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Edge__Fleet__State(str, Enum):
    ZERO     = 'zero'                                                          # no proxies running — $0 baseline
    BOOTING  = 'booting'                                                       # EC2 launched, waiting for readiness
    ACTIVE   = 'active'                                                        # N>=1 proxies serving, in DNS
    SCALING  = 'scaling'                                                       # adding a proxy to an active fleet
    DRAINING = 'draining'                                                      # removed from DNS, waiting connections to drain

    def __str__(self):
        return self.value
