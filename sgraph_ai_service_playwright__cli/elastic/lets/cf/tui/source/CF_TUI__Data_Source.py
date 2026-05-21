# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Data_Source
# The seam every CF-logs screen reads through. traffic_snapshot() returns the one
# normalised Schema__CF_TUI__Traffic_Snapshot; source()/label() identify where it
# came from so the screen can show it honestly. Base class — concrete sources
# (In_Memory / S3) override. Kept thin: subscription to the parsing primitives, no
# parallel state. read_only — the CF-logs view never mutates the bucket.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source        import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Traffic_Snapshot import Schema__CF_TUI__Traffic_Snapshot


class CF_TUI__Data_Source(Type_Safe):

    def source(self) -> Enum__CF_TUI__Source:
        raise NotImplementedError

    def label(self) -> str:                                                          # human-readable origin shown on screen
        raise NotImplementedError

    def traffic_snapshot(self) -> Schema__CF_TUI__Traffic_Snapshot:
        raise NotImplementedError
