# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Function__Details
# Full GetFunction response shaped into typed fields.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Runtime   import Enum__Lambda__Runtime
from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__State      import Enum__Lambda__State
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Arn  import Safe_Str__Lambda__Arn
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name


class Schema__Lambda__Function__Details(Type_Safe):
    name              : Safe_Str__Lambda__Name
    function_arn      : Safe_Str__Lambda__Arn
    runtime           : Enum__Lambda__Runtime = Enum__Lambda__Runtime.PYTHON_3_11
    state             : Enum__Lambda__State   = Enum__Lambda__State.PENDING
    handler           : str                   = ''
    description       : str                   = ''
    memory_size       : int                   = 128
    timeout           : int                   = 60
    last_modified     : str                   = ''
    code_size         : int                   = 0
    role_arn          : str                   = ''
    environment       : dict                  = None   # raw env-var dict (keys only shown by default)
    layers            : list                  = None   # list of layer ARN strings
    architecture      : str                   = ''
    kms_key_arn       : str                   = ''
    tracing_mode      : str                   = ''
    ephemeral_storage : int                   = 512    # MB
    function_url      : str                   = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.environment is None:
            self.environment = {}
        if self.layers is None:
            self.layers = []
