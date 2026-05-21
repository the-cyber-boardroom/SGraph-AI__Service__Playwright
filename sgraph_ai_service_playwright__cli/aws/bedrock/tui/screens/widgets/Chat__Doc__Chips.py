# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Chat__Doc__Chips
# A thin docked row above the composer showing the documents attached to the NEXT
# message (cleared after a send). Hidden when nothing is attached.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.widgets import Static


class Chat__Doc__Chips(Static):
    DEFAULT_CSS = """
    Chat__Doc__Chips { height: auto; padding: 0 1; color: $text-muted; }
    """

    def refresh_from(self, documents) -> None:
        if not documents:
            self.update('')
            self.display = False
            return
        self.display = True
        chips = '  '.join(f'[reverse] {doc.name} · {doc.size}B [/]' for doc in documents)
        self.update(f'[dim]attached →[/] {chips}')
