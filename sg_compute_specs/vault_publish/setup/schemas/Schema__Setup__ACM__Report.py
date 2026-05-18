# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Schema__Setup__ACM__Report
# Result of Setup__ACM.check() — live state of the ACM wildcard certificate.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State


class Schema__Setup__ACM__Report(Type_Safe):
    state       : Enum__Setup__State = Enum__Setup__State.UNKNOWN
    zone        : str  = ''
    cert_arn    : str  = ''
    cert_exists : bool = False
    cert_status : str  = ''
    issues      : List__Schema__Setup__Issue
