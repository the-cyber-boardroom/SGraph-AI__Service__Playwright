# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui widget: Chat__Cost__Meter
# The always-visible session cost/token sidebar. A thin Static fed by the PURE
# cost_meter_markup(session) — the widget holds no logic. refresh_from(session) is
# called after every turn. Provider-agnostic content; a candidate for the shared kit.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.widgets import Static

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Render import cost_meter_markup


class Chat__Cost__Meter(Static):
    DEFAULT_CSS = """
    Chat__Cost__Meter { dock: right; width: 34; padding: 1 2; border: round $surface; }
    """

    def refresh_from(self, session) -> None:
        self.update(cost_meter_markup(session))
