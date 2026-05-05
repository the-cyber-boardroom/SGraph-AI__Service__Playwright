# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Stats
# Control-plane view of a pod's resource snapshot, proxied from the sidecar.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Pod__Stats(Type_Safe):
    container      : str   = ''
    cpu_percent    : float = 0.0
    mem_usage_mb   : float = 0.0
    mem_limit_mb   : float = 0.0
    mem_percent    : float = 0.0
    net_rx_mb      : float = 0.0
    net_tx_mb      : float = 0.0
    block_read_mb  : float = 0.0
    block_write_mb : float = 0.0
    pids           : int   = 0
