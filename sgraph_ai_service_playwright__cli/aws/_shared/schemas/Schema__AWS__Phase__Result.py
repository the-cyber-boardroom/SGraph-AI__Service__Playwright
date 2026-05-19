# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/_shared — Schema__AWS__Phase__Result
# Single timed-phase record used by the aws/* provisioner phase timer.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Phase__Status import Enum__AWS__Phase__Status


class Schema__AWS__Phase__Result(Type_Safe):
    name        : str                      = ''
    status      : Enum__AWS__Phase__Status = None        # populated to PENDING on construction
    duration_ms : int                      = 0
    started_at  : str                      = ''           # ISO-8601 UTC; set on phase-enter
    error       : str                      = ''           # short message
    detail      : str                      = ''           # free-form, e.g. 'reused vpc-...'
