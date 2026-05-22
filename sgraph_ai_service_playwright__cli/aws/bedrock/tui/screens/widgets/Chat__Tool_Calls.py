# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui widget: Chat__Tool_Calls
# A collapsed tool-call section in the transcript (the Claude-style "🔧 N tool calls"
# card). Collapsed by default; expand to see each call's request + response. Built on
# Textual's Collapsible; fed by the PURE tool_calls_* render helpers.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.widgets import Collapsible, Static

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Render import (tool_calls_markup,
                                                                                            tool_calls_title)


class Chat__Tool_Calls(Collapsible):
    DEFAULT_CSS = """
    Chat__Tool_Calls { margin: 0 2; border: round $surface; }
    Chat__Tool_Calls #tool-calls-body { padding: 0 1; }
    """

    def __init__(self, tool_log):
        super().__init__(Static(tool_calls_markup(tool_log), id='tool-calls-body'),
                         title=tool_calls_title(tool_log), collapsed=True)
