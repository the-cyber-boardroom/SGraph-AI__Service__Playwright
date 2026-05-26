# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/user_journey: Schema__UJ__Params__Scale
# Params for uj.scale — the cost-bearing load knob (gated by the execution center).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__UJ__Params__Scale(Type_Safe):
    suite_run_id : str                                                            # the running suite to rescale
    count        : int                                                            # target worker count (load)
    concurrency  : int                                                            # max in flight at once
