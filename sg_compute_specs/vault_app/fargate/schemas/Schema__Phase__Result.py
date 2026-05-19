# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Schema__Phase__Result
# Single timed-phase record: name, lifecycle status, duration, timestamps,
# optional error message, and a free-form detail string.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Phase__Status import Enum__VAF__Phase__Status


class Schema__Phase__Result(Type_Safe):
    name        : str                    = ''
    status      : Enum__VAF__Phase__Status = None            # populated to PENDING on construction
    duration_ms : int                    = 0
    started_at  : str                    = ''                # ISO-8601 UTC; set on phase-enter
    error       : str                    = ''                # short message; full traceback elsewhere
    detail      : str                    = ''                # free-form, e.g. 'state: STOPPED → RUNNING'
