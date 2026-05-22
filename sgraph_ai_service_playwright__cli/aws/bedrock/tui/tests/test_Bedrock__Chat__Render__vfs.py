# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: VFS browser render helpers (pure, 3.11)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Render import (vfs_list_markup,
                                                                                            vfs_detail_markup)


def test_vfs_list_markup_marks_selected():
    markup = vfs_list_markup(['notes.md', 'logs/a.txt'], selected=1)
    assert 'VFS · 2 file(s)' in markup
    assert 'notes.md' in markup and 'logs/a.txt' in markup


def test_vfs_list_markup_empty():
    assert 'no files yet' in vfs_list_markup([], selected=0)


def test_vfs_detail_markup_shows_content():
    markup = vfs_detail_markup('notes.md', 'the answer is 42')
    assert 'notes.md' in markup and 'the answer is 42' in markup
