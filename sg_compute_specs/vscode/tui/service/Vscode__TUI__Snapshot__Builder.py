# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Vscode__TUI__Snapshot__Builder
# Pure: maps a Schema__Vscode__List (what the CLI's `list` produces) into the
# normalised TUI snapshot. No AWS, no logic beyond field projection.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                 import Type_Safe

from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Snapshot import Schema__Vscode__TUI__Snapshot
from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Stack    import Schema__Vscode__TUI__Stack


class Vscode__TUI__Snapshot__Builder(Type_Safe):

    def build(self, listing, can_act: bool = True) -> Schema__Vscode__TUI__Snapshot:
        stacks = [Schema__Vscode__TUI__Stack(stack_name         = str(getattr(s, 'stack_name',   '') or ''),
                                             instance_id        = str(getattr(s, 'instance_id',  '') or ''),
                                             state              = str(getattr(s, 'state',        '') or ''),
                                             distribution       = str(getattr(s, 'distribution', '') or ''),
                                             ingress            = str(getattr(s, 'ingress',      '') or ''),
                                             region             = str(getattr(s, 'region',       '') or ''),
                                             vscode_url         = str(getattr(s, 'vscode_url',   '') or ''),
                                             ssm_forward        = str(getattr(s, 'ssm_forward',  '') or ''),
                                             spot               = bool(getattr(s, 'spot', False)),
                                             time_remaining_sec = int(getattr(s, 'time_remaining_sec', 0) or 0))
                  for s in getattr(listing, 'stacks', [])]
        return Schema__Vscode__TUI__Snapshot(region      = str(getattr(listing, 'region', '') or ''),
                                             captured_at = int(time.time())                          ,
                                             can_act     = bool(can_act)                             ,
                                             total       = len(stacks)                               ,
                                             stacks      = stacks                                    )
