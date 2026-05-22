# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Change_Log
# Holds a tool's change entries and renders them to the whatsnew.md / changelog.md
# the VFS doc tree serves. Capture is RECOMMENDED, not enforced (decision #5) — a
# minimal provider can ship with an empty log.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Change_Kind import Enum__Tui_Api__Change_Kind
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Change    import List__Tui_Api__Change
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Change  import Schema__Tui_Api__Change


class Tui_Api__Change_Log(Type_Safe):
    changes : List__Tui_Api__Change

    def add(self, kind: Enum__Tui_Api__Change_Kind, summary: str, version: str, ts: float = 0.0) -> 'Tui_Api__Change_Log':
        self.changes.append(Schema__Tui_Api__Change(kind=kind, summary=summary, version=version, ts=ts))
        return self

    def recent(self, limit: int = 10) -> list:                                    # most-recent-first
        return list(self.changes)[-limit:][::-1]

    def whatsnew_markdown(self, limit: int = 10) -> str:
        lines = ["# What's new", '']
        for change in self.recent(limit):
            lines.append(f'- **{change.kind}** ({change.version}) — {change.summary}')
        return '\n'.join(lines)

    def changelog_markdown(self) -> str:
        lines = ['# Changelog', '']
        for change in reversed(list(self.changes)):
            lines.append(f'- **{change.kind}** {change.version}: {change.summary}')
        return '\n'.join(lines)
