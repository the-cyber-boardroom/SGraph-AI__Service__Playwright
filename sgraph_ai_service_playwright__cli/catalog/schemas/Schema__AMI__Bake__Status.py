# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__AMI__Bake__Status
# Included in stack-create responses when creation_mode == BAKE_AMI.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__AMI__Bake__State             import Enum__AMI__Bake__State
from sgraph_ai_service_playwright__cli.catalog.primitives.Safe_Str__AWS__AMI_Id         import Safe_Str__AWS__AMI_Id
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime          import Safe_Str__ISO_Datetime


class Schema__AMI__Bake__Status(Type_Safe):
    state          : Enum__AMI__Bake__State  = Enum__AMI__Bake__State.BAKING
    target_ami_id  : Safe_Str__AWS__AMI_Id                                    # empty while baking; populated when READY
    started_at     : Safe_Str__ISO_Datetime
