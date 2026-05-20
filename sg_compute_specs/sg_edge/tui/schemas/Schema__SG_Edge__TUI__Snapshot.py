# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Schema__SG_Edge__TUI__Snapshot
# The one normalised, source-independent snapshot every TUI screen renders. Built
# by SG_Edge__TUI__Snapshot__Builder from either the local stack or the live AWS
# edge DNS. `capabilities` names which panes have real data (the rest render a
# labelled pending state). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.schemas.List__SG_Edge__IP                     import List__SG_Edge__IP
from sg_compute_specs.sg_edge.local.schemas.List__Local__Edge__Issue        import List__Local__Edge__Issue
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Target          import Enum__SG_Edge__TUI__Target
from sg_compute_specs.sg_edge.tui.schemas.List__SG_Edge__TUI__Slug          import List__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.List__SG_Edge__TUI__Capability    import List__SG_Edge__TUI__Capability


class Schema__SG_Edge__TUI__Snapshot(Type_Safe):
    parent       : str                                                               # the edge parent zone this snapshot describes
    target       : Enum__SG_Edge__TUI__Target = Enum__SG_Edge__TUI__Target.LOCAL      # which source produced it
    deployed     : bool = False                                                      # local: stack marker; aws: zone present
    zone_exists  : bool = False                                                      # hosted zone present
    wildcard     : bool = False                                                      # *.<parent> A present (CloudFront equivalent)
    fleet_ips    : List__SG_Edge__IP                                                 # proxies.<parent> A values
    zero_streak  : int  = 0                                                          # _state.<parent> idle counter
    slugs        : List__SG_Edge__TUI__Slug                                          # registered + backed slugs
    issues       : List__Local__Edge__Issue                                          # deviation findings (reused from the local check vocabulary)
    capabilities : List__SG_Edge__TUI__Capability                                    # panes with real data (cost/throughput/instances absent today)
    captured_at  : int  = 0                                                          # unix seconds the snapshot was taken
