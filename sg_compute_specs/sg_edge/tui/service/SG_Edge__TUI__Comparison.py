# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Comparison
# Pure: diff a LOCAL snapshot against an AWS snapshot for Screen 3. Honest two-way
# only (local vs edge) — there is no "Deployed" third column and no cross-service
# version matrix; both are out of scope for this sg_edge tool. A row is IN_SYNC when
# both sides agree (both present OR both absent), else names the side that has it.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Sync_State           import Enum__SG_Edge__TUI__Sync_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Comparison_Row   import Schema__SG_Edge__TUI__Comparison_Row
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot         import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.schemas.List__SG_Edge__TUI__Comparison_Row     import List__SG_Edge__TUI__Comparison_Row


class SG_Edge__TUI__Comparison(Type_Safe):

    def compare(self, local : Schema__SG_Edge__TUI__Snapshot,
                      aws   : Schema__SG_Edge__TUI__Snapshot) -> List__SG_Edge__TUI__Comparison_Row:
        rows = List__SG_Edge__TUI__Comparison_Row()
        self.add(rows, 'wildcard',    bool(local.wildcard),            bool(aws.wildcard))
        self.add(rows, 'proxy fleet', len(local.fleet_ips) > 0,        len(aws.fleet_ips) > 0)

        local_slugs = {s.slug for s in local.slugs}
        aws_slugs   = {s.slug for s in aws.slugs}
        for slug in sorted(local_slugs | aws_slugs):
            self.add(rows, f'slug:{slug}', slug in local_slugs, slug in aws_slugs)
        return rows

    def add(self, rows, name : str, local_present : bool, edge_present : bool) -> None:
        if   local_present == edge_present : sync = Enum__SG_Edge__TUI__Sync_State.IN_SYNC
        elif local_present                 : sync = Enum__SG_Edge__TUI__Sync_State.LOCAL_ONLY
        else                               : sync = Enum__SG_Edge__TUI__Sync_State.EDGE_ONLY
        rows.append(Schema__SG_Edge__TUI__Comparison_Row(name          = name,
                                                         local_present = local_present,
                                                         edge_present  = edge_present,
                                                         sync_state    = sync))
