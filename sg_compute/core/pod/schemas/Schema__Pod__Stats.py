# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Stats
# Control-plane view of a pod's resource snapshot, proxied from the sidecar.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.primitives.Safe_Int__Pids   import Safe_Int__Pids
from sg_compute.primitives.Safe_Str__Pod__Name import Safe_Str__Pod__Name


class Schema__Pod__Stats(Type_Safe):
    container      : Safe_Str__Pod__Name = Safe_Str__Pod__Name()
    cpu_percent    : float = 0.0
    mem_usage_mb   : float = 0.0
    mem_limit_mb   : float = 0.0
    mem_percent    : float = 0.0
    net_rx_mb      : float = 0.0
    net_tx_mb      : float = 0.0
    block_read_mb  : float = 0.0
    block_write_mb : float = 0.0
    pids           : Safe_Int__Pids = Safe_Int__Pids()
