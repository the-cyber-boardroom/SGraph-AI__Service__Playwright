# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__CLI__Health__Probe
# Return value from spec.health() — instant or polled readiness check.
# last_error is plain str because Safe_Str normalises spaces to underscores
# which makes error messages unreadable.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe    import Type_Safe


class Schema__CLI__Health__Probe(Type_Safe):
    healthy      : bool             = False
    state        : str              = ''
    elapsed_ms   : int              = 0
    last_error   : str              = ''
    cert_summary : str              = ''             # served-cert one-liner when the vault was reached over HTTPS
