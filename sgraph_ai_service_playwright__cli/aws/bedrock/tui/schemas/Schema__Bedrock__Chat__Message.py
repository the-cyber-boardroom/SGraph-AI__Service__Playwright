# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Schema__Bedrock__Chat__Message
# One line of the conversation. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.enums.Enum__Bedrock__Chat__Role import Enum__Bedrock__Chat__Role


class Schema__Bedrock__Chat__Message(Type_Safe):
    role : Enum__Bedrock__Chat__Role                                              # user / assistant / system
    text : str                                                                    # message content
    ts   : float                                                                  # epoch seconds (capture moment)
