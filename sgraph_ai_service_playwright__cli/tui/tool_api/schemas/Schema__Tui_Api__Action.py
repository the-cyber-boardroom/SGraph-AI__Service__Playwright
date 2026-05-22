# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Action
# One invocable action. input_schema is REAL JSON Schema derived from a Type_Safe
# params class (Tui_Api__Schema__Builder). preconditions / privileges / supports_dry_run
# / emits are added in B2/B3. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier            import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.primitives.Safe_Str__Tui_Api__Action_Name import Safe_Str__Tui_Api__Action_Name
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Precondition   import List__Tui_Api__Precondition
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Privilege      import List__Tui_Api__Privilege
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope        import Schema__Tui_Api__Scope


class Schema__Tui_Api__Action(Type_Safe):
    name             : Safe_Str__Tui_Api__Action_Name
    description      : str
    input_schema     : dict                                                       # real JSON Schema (from a Type_Safe params class)
    output_schema    : dict
    tier             : Enum__Tui_Api__Tier = Enum__Tui_Api__Tier.READ_ONLY
    scope            : Schema__Tui_Api__Scope
    privileges       : List__Tui_Api__Privilege                                   # per-action backing grants (override the API baseline)
    preconditions    : List__Tui_Api__Precondition                               # sequencing/state gates (§4.2)
    supports_dry_run : bool  = False                                              # can the execution center preview it without committing?
    est_cost_usd     : float = 0.0                                                # static hint; the center records the actual cost
    idempotent       : bool  = True
