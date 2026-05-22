# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Loadout
# The live, time-bounded grant set a chat operates under (assembled from a workflow
# or a --tools flag). Provider-agnostic — the Bedrock toolConfig mapping is chat-side.
# Pure data; the assembly logic lives in Tui_Api__Loadout__Assembler. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Grant import List__Tui_Api__Grant


class Schema__Tui_Api__Loadout(Type_Safe):
    grants     : List__Tui_Api__Grant
    workflow   : str                                                              # provenance: which workflow assembled this
    budget_usd : float = 0.0                                                      # optional spend ceiling for the whole loadout
