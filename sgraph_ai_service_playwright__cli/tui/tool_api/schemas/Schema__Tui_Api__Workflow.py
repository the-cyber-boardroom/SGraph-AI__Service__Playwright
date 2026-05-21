# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Workflow
# The curation unit (e.g. 'diagnose-edge-issue'): a named set of SG/Role grants the
# system hands an agent. The model never picks its own tools (decision #10) — a
# workflow is the source of truth. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Grant import List__Tui_Api__Grant


class Schema__Tui_Api__Workflow(Type_Safe):
    name        : str
    description : str
    grants      : List__Tui_Api__Grant                                            # the capability tokens this workflow grants
