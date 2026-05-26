# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/user_journey: Schema__UJ__Params__Suite_Run_Ref
# Params for actions that target one running suite. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__UJ__Params__Suite_Run_Ref(Type_Safe):
    suite_run_id : str                                                            # the running suite to target
