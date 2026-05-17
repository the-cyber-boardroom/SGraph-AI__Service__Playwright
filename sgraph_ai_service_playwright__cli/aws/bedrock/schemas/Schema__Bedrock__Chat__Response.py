# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Bedrock__Chat__Response
# Result of a single Bedrock converse call — tokens, cost estimate, body text.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id import Safe_Str__Bedrock__Model_Id


class Schema__Bedrock__Chat__Response(Type_Safe):
    model_id         : Safe_Str__Bedrock__Model_Id                                  # Resolved model ID used in the call
    region           : str                                                            # AWS region of the call
    prompt           : str                                                            # User-supplied prompt text
    response_text    : str                                                            # Full response content
    input_tokens     : int                                                            # Input token count from usage metadata
    output_tokens    : int                                                            # Output token count from usage metadata
    cost_usd         : float                                                          # Estimated cost in USD
    run_id           : str                                                            # UUID for the capture file
    iso_day          : str                                                            # ISO date YYYY-MM-DD for capture path
    capture_path     : str                                                            # Absolute path to the written capture file
