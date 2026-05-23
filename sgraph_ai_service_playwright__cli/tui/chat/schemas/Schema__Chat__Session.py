# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Session — neutral, ephemeral conversation state.
# No AWS (region etc. live in the backend config). Pure data — engine maintains aggregates.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Message import List__Chat__Message
from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Turn    import List__Chat__Turn


class Schema__Chat__Session(Type_Safe):
    session_id          : str
    backend_id          : str
    model_id            : str
    started_at          : float = 0.0
    system_prompt       : str
    context_label       : str
    messages            : List__Chat__Message
    turns               : List__Chat__Turn
    total_input_tokens  : int   = 0
    total_output_tokens : int   = 0
    total_cost_usd      : float = 0.0
    turn_count          : int   = 0
    budget_usd          : float = 0.50
