# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Wait__Tick
# One snapshot emitted by Elastic__Service.wait_until_ready via its
# on_progress callback. Carries everything the CLI needs to render a single
# live spinner line — attempt counter, current instance Info, Kibana probe
# status, and a pre-rendered human message the service composes so the CLI
# stays dumb.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Kibana__Probe__Status    import Enum__Kibana__Probe__Status
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Info        import Schema__Elastic__Info


class Schema__Wait__Tick(Type_Safe):
    attempt      : int                              = 0
    info         : Schema__Elastic__Info
    probe        : Enum__Kibana__Probe__Status      = Enum__Kibana__Probe__Status.UNKNOWN
    message      : Safe_Str__Text                                                   # Human-readable, e.g. "nginx up but Kibana container still booting (502)"
    elapsed_ms   : int                              = 0                             # Since wait_until_ready started — for CLI progress display
