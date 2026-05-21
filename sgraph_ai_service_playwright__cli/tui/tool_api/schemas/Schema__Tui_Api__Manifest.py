# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Manifest
# One TUI API's machine-readable contract (a tool may expose several — §4.4).
# scopes / privileges / children are added in B2/fractal slices. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.primitives.Safe_Str__Tui_Api__Slug import Safe_Str__Tui_Api__Slug
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action       import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Event        import List__Tui_Api__Event
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier         import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Skills     import Schema__Tui_Api__Skills


class Schema__Tui_Api__Manifest(Type_Safe):
    slug        : Safe_Str__Tui_Api__Slug                                         # 'sg-aws.s3'
    tool        : Safe_Str__Tui_Api__Slug                                         # 'sg-aws' (owning tool)
    name        : str
    version     : str = '0.1.0'
    description : str
    tiers       : List__Tui_Api__Tier
    actions     : List__Tui_Api__Action
    events      : List__Tui_Api__Event
    skills      : Schema__Tui_Api__Skills
