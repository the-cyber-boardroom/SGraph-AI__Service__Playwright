# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Privilege
# The backing grant a scope maps to (the privilege the resolver checks). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Priv_Kind import Enum__Tui_Api__Priv_Kind


class Schema__Tui_Api__Privilege(Type_Safe):
    kind : Enum__Tui_Api__Priv_Kind = Enum__Tui_Api__Priv_Kind.SG_ROLE
    ref  : str                                                                    # creds scope name / policy action / role ARN / env var / vault key
    note : str
