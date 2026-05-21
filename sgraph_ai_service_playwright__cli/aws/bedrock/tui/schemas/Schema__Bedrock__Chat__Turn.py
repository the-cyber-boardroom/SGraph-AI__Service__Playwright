# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Schema__Bedrock__Chat__Turn
# Cost / telemetry record for one user→assistant exchange. Pure data — no methods.
# The aggregates on the session are running sums of these.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id import Safe_Str__Bedrock__Model_Id


class Schema__Bedrock__Chat__Turn(Type_Safe):
    model_id      : Safe_Str__Bedrock__Model_Id                                   # model that answered this turn
    input_tokens  : int                                                           # from the stream metadata event (exact, not estimated)
    output_tokens : int
    cost_usd      : float                                                         # Bedrock__Cost__Calculator.estimate(...)
    latency_ms    : int                                                           # from metadata.metrics.latencyMs
    ts            : float                                                         # epoch seconds (turn completion)
    request_json  : str                                                           # exact Converse request body sent (modelId + system + full messages)
    response_text : str                                                           # exact assistant text returned
