# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Schema__Setup__IAM__Report
# Result of Setup__IAM.check() — current state of the waker execution role.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue   import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State               import Enum__Setup__State


class Schema__Setup__IAM__Report(Type_Safe):
    state                : Enum__Setup__State = Enum__Setup__State.UNKNOWN
    role_name            : str                = ''
    role_arn             : str                = ''
    role_exists          : bool               = False
    policy_name          : str                = ''    # name of the inline policy we own
    policy_matches       : bool               = False  # True when live policy == template
    trust_policy_ok      : bool               = False  # True when trust policy is Lambda
    missing_statements   : str                = ''    # summary of statements in template but not live
    extra_statements     : str                = ''    # summary of statements in live but not template
    issues               : List__Schema__Setup__Issue
