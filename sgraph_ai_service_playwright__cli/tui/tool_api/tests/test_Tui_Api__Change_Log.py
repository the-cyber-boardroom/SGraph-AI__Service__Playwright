# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Change_Log
# Change entries render to whatsnew (most-recent-first) + changelog markdown. 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Change_Kind import Enum__Tui_Api__Change_Kind
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Change_Log      import Tui_Api__Change_Log


def test_add_is_chainable_and_whatsnew_is_recent_first():
    log = (Tui_Api__Change_Log().add(Enum__Tui_Api__Change_Kind.FEATURE, 'added X', '0.1.0')
                                .add(Enum__Tui_Api__Change_Kind.FIX,     'fixed Y', '0.1.1'))
    whatsnew = log.whatsnew_markdown()
    assert 'added X' in whatsnew and 'fixed Y' in whatsnew
    assert whatsnew.index('fixed Y') < whatsnew.index('added X')                  # most recent first
    assert 'feature' in whatsnew and 'fix' in whatsnew


def test_changelog_lists_all():
    log = (Tui_Api__Change_Log().add(Enum__Tui_Api__Change_Kind.FEATURE, 'one', '0.1.0')
                                .add(Enum__Tui_Api__Change_Kind.BREAKING, 'two', '0.2.0'))
    changelog = log.changelog_markdown()
    assert 'one' in changelog and 'two' in changelog and 'breaking' in changelog


def test_empty_log_renders_cleanly():
    assert "What's new" in Tui_Api__Change_Log().whatsnew_markdown()
