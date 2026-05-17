# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Bedrock__Check__Result
# One row in the Bedrock preflight diagnostic table.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Check__Status import Enum__Bedrock__Check__Status


class Schema__Bedrock__Check__Result(Type_Safe):
    check_name : str                                                               # Short label e.g. 'sts identity'
    status     : Enum__Bedrock__Check__Status                                      # PASS / WARN / FAIL
    message    : str                                                               # One-line result message
    hint       : str                                                               # Actionable next-step hint (empty on PASS)
