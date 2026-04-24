# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_UInt__Max_Hours
# Auto-delete window in hours. 0 means "no timeout" per the CLI convention
# (see scripts.provision_ec2). Upper bound of 168 keeps ephemerality sane.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt                                import Safe_UInt


class Safe_UInt__Max_Hours(Safe_UInt):
    min_value = 0
    max_value = 168                                                                 # 7 days
