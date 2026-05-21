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

    def list_files(self, date_iso : str = '', hour : str = '', max_files : int = 0):  # → List__CF_TUI__File_Row (flat, scoped — the no-TTY listing)
        raise NotImplementedError

    def list_dir(self, prefix : str = ''):                                           # → List__CF_TUI__Dir_Entry (folder browser: child folders + files at this level)
        raise NotImplementedError

    def read_file(self, key : str):                                                  # → Schema__CF_TUI__File_View (drill into one object)
        raise NotImplementedError

    def read_record(self, key : str, line_index : int = 0):                          # → Schema__CF_TUI__Record_View (one line, all fields, lineage)
        raise NotImplementedError
