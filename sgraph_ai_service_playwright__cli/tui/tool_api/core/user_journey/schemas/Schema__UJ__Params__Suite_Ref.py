# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/user_journey: Schema__UJ__Params__Suite_Ref
# Params for uj.start — names a vault-stored suite definition. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__UJ__Params__Suite_Ref(Type_Safe):
    suite_id : str                                                                # vault-stored suite definition to launch
