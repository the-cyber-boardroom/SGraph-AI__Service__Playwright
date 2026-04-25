# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Exec__Result
# Captured outcome of `sp elastic exec NAME "command"`. SSM Run Command
# returns stdout, stderr, and a ResponseCode (the shell exit code). We carry
# all three plus wall-clock duration so the CLI can render a useful one-line
# summary.
#
# stdout / stderr use Safe_Str__Shell__Output (permissive: keeps newlines,
# slashes, colons, backticks). Up to 1 MB each — past that, route via S3.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Shell__Output   import Safe_Str__Shell__Output


class Schema__Exec__Result(Type_Safe):
    stack_name  : Safe_Str__Elastic__Stack__Name
    instance_id : Safe_Str__Instance__Id
    command     : Safe_Str__Shell__Output                                           # Permissive — commands legitimately contain quotes / pipes / redirects
    stdout      : Safe_Str__Shell__Output
    stderr      : Safe_Str__Shell__Output
    exit_code   : int                              = 0                              # SSM ResponseCode; -1 for "no result" (timeout / not run)
    duration_ms : int                              = 0
    status      : Safe_Str__Text                                                    # SSM Status: Success / Failed / Cancelled / TimedOut / etc.
