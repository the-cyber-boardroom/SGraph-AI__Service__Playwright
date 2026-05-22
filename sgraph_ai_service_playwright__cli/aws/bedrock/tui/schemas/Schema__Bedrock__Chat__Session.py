# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Schema__Bedrock__Chat__Session
# In-memory, ephemeral conversation state — lost on close by design (cost data is
# fine to discard; durable capture is the opt-in export/brief action). Pure data —
# no methods; the engine maintains the aggregates.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Session_Id   import Safe_Str__Bedrock__Session_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.List__Bedrock__Chat__Message    import List__Bedrock__Chat__Message
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.List__Bedrock__Chat__Turn       import List__Bedrock__Chat__Turn


class Schema__Bedrock__Chat__Session(Type_Safe):
    session_id          : Safe_Str__Bedrock__Session_Id
    provider            : str  = 'nova'                                           # Nova-only for v1
    model_alias         : str  = 'default'                                        # 'default' resolves to nova-lite
    region              : str                                                     # resolved at session start
    started_at          : float
    system_prompt       : str                                                     # built from a seeded context (may be empty)
    context_label       : str                                                     # short UI label for the seeded context (may be empty)
    messages            : List__Bedrock__Chat__Message
    turns               : List__Bedrock__Chat__Turn
    total_input_tokens  : int                                                     # running aggregates (engine maintains)
    total_output_tokens : int
    total_cost_usd      : float
    turn_count          : int
    budget_usd          : float = 0.50                                            # soft session budget for the meter
