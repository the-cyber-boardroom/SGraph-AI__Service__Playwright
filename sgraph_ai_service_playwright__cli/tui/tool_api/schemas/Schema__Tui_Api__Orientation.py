# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Orientation
# The "I just arrived — now what?" surface: live status + recent changes + refs to
# the VFS doc files. The dynamic available-actions list is provided live by the
# execution center (B3), not stored here. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Change import List__Tui_Api__Change


class Schema__Tui_Api__Orientation(Type_Safe):
    tool           : str
    status         : dict                                                         # live: {healthy: bool, note: str, ...}
    recent_changes : List__Tui_Api__Change                                        # the whatsnew feed (most-recent-first when rendered)
    skills_ref     : str = 'skills.md'                                            # VFS path under /tools/<tool>/
    whatsnew_ref   : str = 'whatsnew.md'
