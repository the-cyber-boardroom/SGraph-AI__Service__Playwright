# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Vscode__TUI__Data_Source
# The seam the screen + provider read through. It owns NO logic — snapshot() and
# the action methods delegate to the SAME Vscode__Service the `sg vscode` CLI uses
# (separation guide). Tests inject a stub service (a fake, not a mock) exposing
# list_stacks / delete_stack — no AWS, no patching.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.vscode.service.Vscode__Service                        import Vscode__Service, DEFAULT_REGION
from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Snapshot      import Schema__Vscode__TUI__Snapshot
from sg_compute_specs.vscode.tui.service.Vscode__TUI__Snapshot__Builder     import Vscode__TUI__Snapshot__Builder


class Vscode__TUI__Data_Source(Type_Safe):
    service : Optional[Vscode__Service]         = None
    builder : Vscode__TUI__Snapshot__Builder    = None
    region  : str                               = DEFAULT_REGION

    def setup(self) -> 'Vscode__TUI__Data_Source':
        if self.service is None:
            self.service = Vscode__Service().setup()
        if self.builder is None:
            self.builder = Vscode__TUI__Snapshot__Builder()
        return self

    def can_act(self) -> bool:                                                       # vscode mutations (delete) are real → always actionable
        return True

    def snapshot(self) -> Schema__Vscode__TUI__Snapshot:
        listing = self.service.list_stacks(self.region)
        return (self.builder or Vscode__TUI__Snapshot__Builder()).build(listing, self.can_act())

    def delete(self, stack_name: str) -> bool:
        result = self.service.delete_stack(self.region, stack_name)
        return bool(getattr(result, 'deleted', False))
