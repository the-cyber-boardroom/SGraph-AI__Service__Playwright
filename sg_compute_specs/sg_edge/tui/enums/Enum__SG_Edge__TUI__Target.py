# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Enum__SG_Edge__TUI__Target
# Which data source a snapshot was produced from: the file-backed local edge
# (edge.sg-labs.local) or the live AWS edge DNS (edge.sg-labs.app, read-only today).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__SG_Edge__TUI__Target(str, Enum):
    LOCAL = 'local'
    AWS   = 'aws'

    def __str__(self):
        return self.value
