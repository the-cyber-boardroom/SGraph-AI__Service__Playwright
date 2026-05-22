# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Content (neutral content block)
# One block of a message — exactly one of text / document / tool_use / tool_result is
# set. The backend adapter translates these to/from its wire format. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Document    import Schema__Chat__Document
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool_Result import Schema__Chat__Tool_Result
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool_Use    import Schema__Chat__Tool_Use


class Schema__Chat__Content(Type_Safe):
    text        : str                          = ''                               # plain text (the common case)
    document    : Schema__Chat__Document        = None                            # an attached document
    tool_use    : Schema__Chat__Tool_Use        = None                            # the model asking to call a tool
    tool_result : Schema__Chat__Tool_Result     = None                            # the result fed back
