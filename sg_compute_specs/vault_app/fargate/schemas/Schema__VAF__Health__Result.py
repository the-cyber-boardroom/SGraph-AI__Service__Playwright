# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Schema__VAF__Health__Result
# Result of an HTTP health poll from Vault_App__Fargate__Health.wait_for().
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__VAF__Health__Result(Type_Safe):
    ok          : bool = False
    status_code : int  = 0
    attempts    : int  = 0
    duration_ms : int  = 0
    last_error  : str  = ''
    url         : str  = ''
