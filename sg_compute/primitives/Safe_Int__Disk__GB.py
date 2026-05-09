# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Disk__GB
# EBS root volume size in GiB. Zero means: use the AMI's default volume size.
# Upper bound matches the gp3 maximum (16 TiB).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Disk__GB(Safe_Int):
    min_value = 0
    max_value = 16384
