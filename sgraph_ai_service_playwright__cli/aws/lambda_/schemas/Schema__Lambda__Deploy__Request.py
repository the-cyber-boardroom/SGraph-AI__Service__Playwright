# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Deploy__Request
# Input for Lambda__Deployer.deploy_from_folder().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Runtime           import Enum__Lambda__Runtime
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name     import Safe_Str__Lambda__Name


class Schema__Lambda__Deploy__Request(Type_Safe):
    name        : Safe_Str__Lambda__Name
    folder_path : str                    = ''
    handler     : str                    = ''                                             # e.g. 'handler:handler'
    role_arn    : str                    = ''                                             # IAM execution role ARN
    runtime     : Enum__Lambda__Runtime  = Enum__Lambda__Runtime.PYTHON_3_11
    memory_size : int                    = 256
    timeout     : int                    = 900
    description : str                    = ''
