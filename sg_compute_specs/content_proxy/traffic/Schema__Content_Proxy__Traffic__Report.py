# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Traffic__Report
# Aggregate accuracy + latency over a corpus run. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Schema__Content_Proxy__Traffic__Report(Type_Safe):
    total          : int   = 0
    passed         : int   = 0
    failed         : int   = 0
    accuracy_pct   : float = 0.0
    latency_p50_ms : int   = 0
    latency_p95_ms : int   = 0
