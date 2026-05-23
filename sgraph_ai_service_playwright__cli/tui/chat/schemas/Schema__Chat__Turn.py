# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Turn — neutral per-turn cost/telemetry record.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Tool_Call import List__Chat__Tool_Call


class Schema__Chat__Turn(Type_Safe):
    model_id      : str
    input_tokens  : int   = 0
    output_tokens : int   = 0
    cost_usd      : float = 0.0
    latency_ms    : int   = 0
    ts            : float = 0.0
    request_json  : str                                                           # exact request body sent (for the Inspector)
    response_text : str                                                           # final assistant text
    model_calls   : int   = 1                                                     # converse round-trips this turn
    tool_calls    : int   = 0
    tool_log      : List__Chat__Tool_Call                                         # per-tool detail
    estimated     : bool  = False                                                 # cost is an estimate (backend omitted tokens)
