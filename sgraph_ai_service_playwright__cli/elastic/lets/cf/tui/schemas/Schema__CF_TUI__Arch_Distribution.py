# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Arch_Distribution
# One CloudFront distribution as the architecture view shows it. rt_log_status is
# UNVERIFIED because whether a given distribution's real-time logs feed the Firehose
# is not introspectable via `sg aws` — surfaced honestly, never assumed. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__Arch_Distribution(Type_Safe):
    distribution_id : str
    domain          : str
    aliases         : str                                                            # comma-joined CNAMEs
    status          : str
    enabled         : bool = True
    rt_log_status   : str  = 'UNVERIFIED'                                            # real-time-log → Firehose wiring is not introspectable
