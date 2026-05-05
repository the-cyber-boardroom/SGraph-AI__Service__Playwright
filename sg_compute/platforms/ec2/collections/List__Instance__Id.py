# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — List__Instance__Id
# Ordered list of EC2 instance ids. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id                     import Safe_Str__Instance__Id


class List__Instance__Id(Type_Safe__List):
    expected_type = Safe_Str__Instance__Id
