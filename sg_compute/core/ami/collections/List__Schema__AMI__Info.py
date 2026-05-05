# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — List__Schema__AMI__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute.core.ami.schemas.Schema__AMI__Info import Schema__AMI__Info


class List__Schema__AMI__Info(Type_Safe__List):
    expected_type = Schema__AMI__Info
