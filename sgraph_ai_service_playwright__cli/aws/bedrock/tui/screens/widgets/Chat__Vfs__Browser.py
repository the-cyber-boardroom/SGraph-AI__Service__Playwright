# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui widget: Chat__Vfs__Browser
# An openable right-hand panel listing the session VFS's files + a preview of the
# selected one. Shares the right slot with the cost meter + inspector (F3 toggles it).
# Thin — fed by the PURE vfs render helpers; reads via the VFS provider's READ_ONLY
# state()/vfs.read, so opening it never mutates. Hidden by default.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.containers import Vertical, VerticalScroll
from textual.widgets    import Static

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Render import (vfs_list_markup,
                                                                                            vfs_detail_markup)


class Chat__Vfs__Browser(Vertical):
    DEFAULT_CSS = """
    Chat__Vfs__Browser { dock: right; width: 64; border: round $accent; padding: 0 1; }
    Chat__Vfs__Browser #vfs-list { height: auto; max-height: 40%; }
    Chat__Vfs__Browser #vfs-detail-scroll { height: 1fr; }
    """

    def compose(self):
        yield Static('', id='vfs-list')
        with VerticalScroll(id='vfs-detail-scroll'):
            yield Static('', id='vfs-detail')

    def refresh_from(self, provider, selected: int = 0) -> None:
        if provider is None:
            self.query_one('#vfs-list',   Static).update('[dim]no VFS — enable tools (ctrl+g → core.vfs)[/]')
            self.query_one('#vfs-detail', Static).update('')
            return
        files = list(provider.state().get('files', []))
        self.query_one('#vfs-list', Static).update(vfs_list_markup(files, selected))
        if files:
            path    = files[max(0, min(selected, len(files) - 1))]
            content = ''
            try:
                result = provider.dispatch('vfs.read', {'path': path})            # READ_ONLY — no mutation
                if result.ok:
                    content = result.json().get('data', {}).get('result', '')
            except Exception as exc:
                content = f'(could not read: {exc})'
            self.query_one('#vfs-detail', Static).update(vfs_detail_markup(path, content))
        else:
            self.query_one('#vfs-detail', Static).update('[dim](empty)[/]')
