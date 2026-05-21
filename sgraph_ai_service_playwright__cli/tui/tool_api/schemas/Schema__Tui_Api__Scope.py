# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Scope
# The capability descriptor an action lives under. String form: {api}:{capability}[:{resource}]
# carried by an SG/Role token (B2). capability '*' = the whole API. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.primitives.Safe_Str__Tui_Api__Capability import Safe_Str__Tui_Api__Capability
from sgraph_ai_service_playwright__cli.tui.tool_api.primitives.Safe_Str__Tui_Api__Slug       import Safe_Str__Tui_Api__Slug


class Schema__Tui_Api__Scope(Type_Safe):
    api        : Safe_Str__Tui_Api__Slug                                          # owning API slug, e.g. 'sg-aws.s3'
    capability : Safe_Str__Tui_Api__Capability                                    # 'read' | 'write' | 'list_objects' | '*'
    resource   : str = '*'                                                        # optional qualifier / glob, e.g. a bucket or slug
