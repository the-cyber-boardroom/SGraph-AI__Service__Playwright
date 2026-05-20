# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Enum__SG_Edge__TUI__Capability
# Which panes a snapshot can back with REAL data. A screen checks membership before
# rendering a pane; absent capabilities render an explicit "pending" placeholder
# rather than fabricated numbers (the no-fabrication rule, made first-class).
#
#   TOPOLOGY / SLUGS / CHECKS / FLEET — real today (DNS-grounded)
#   COST / THROUGHPUT / INSTANCES     — pending Slice 5 (live EC2) + observability
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__SG_Edge__TUI__Capability(str, Enum):
    TOPOLOGY   = 'topology'
    SLUGS      = 'slugs'
    CHECKS     = 'checks'
    FLEET      = 'fleet'
    COST       = 'cost'                                                              # pending — needs live EC2 + pricing
    THROUGHPUT = 'throughput'                                                        # pending — needs proxy stats / observability
    INSTANCES  = 'instances'                                                         # pending — needs the EC2 launcher (Slice 5)

    def __str__(self):
        return self.value
