# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Schema__Setup__EC2__Report
# Result of Setup__EC2.check() — pre-flight check that the *shared* EC2
# prerequisites for launching a vault-app instance are in place.
# Each register creates a fresh EC2 stack, so there's no "default" instance
# to verify — only the global resources used by every launch.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State


class Schema__Setup__EC2__Report(Type_Safe):
    state                : Enum__Setup__State = Enum__Setup__State.UNKNOWN
    region               : str  = ''
    profile_name         : str  = ''
    profile_exists       : bool = False
    profile_arn          : str  = ''
    ami_id               : str  = ''
    ami_resolvable       : bool = False
    issues               : List__Schema__Setup__Issue
