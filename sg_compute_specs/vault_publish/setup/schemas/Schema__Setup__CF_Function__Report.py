# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Schema__Setup__CF_Function__Report
# Result of Setup__CF__Function.check() — live state of the viewer-host CF
# Function and whether it is attached to the wildcard distribution.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State


class Schema__Setup__CF_Function__Report(Type_Safe):
    state            : Enum__Setup__State = Enum__Setup__State.UNKNOWN
    zone             : str  = ''
    function_name    : str  = ''
    function_arn     : str  = ''
    function_exists  : bool = False
    function_stage   : str  = ''                                                      # LIVE when published
    code_matches     : bool = False                                                    # live code == expected JS source
    attached         : bool = False                                                    # arn appears on distribution viewer-request
    distribution_id  : str  = ''
    issues           : List__Schema__Setup__Issue
