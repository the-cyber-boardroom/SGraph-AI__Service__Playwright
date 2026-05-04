# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Shell__Execute__Request
# Body for POST /host/shell/execute. Command is validated against the allowlist
# in Shell__Executor before any subprocess is spawned.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe

from sgraph_ai_service_playwright__host.shell.primitives.Safe_Str__Shell__Command           import Safe_Str__Shell__Command


class Schema__Shell__Execute__Request(Type_Safe):
    command     : Safe_Str__Shell__Command
    timeout     : int = 30          # seconds; max enforced by Shell__Executor
    working_dir : str = ''
