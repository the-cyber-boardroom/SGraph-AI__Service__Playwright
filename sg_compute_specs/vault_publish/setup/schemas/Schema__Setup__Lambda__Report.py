# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Schema__Setup__Lambda__Report
# Result of Setup__Lambda.check() — live state of the waker Lambda function.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State


class Schema__Setup__Lambda__Report(Type_Safe):
    state           : Enum__Setup__State = Enum__Setup__State.UNKNOWN
    function_name   : str  = ''
    function_arn    : str  = ''
    function_exists : bool = False
    runtime_ok      : bool = False
    handler_ok      : bool = False
    memory_ok       : bool = False
    timeout_ok      : bool = False
    url_exists      : bool = False
    function_url    : str  = ''
    issues          : List__Schema__Setup__Issue
