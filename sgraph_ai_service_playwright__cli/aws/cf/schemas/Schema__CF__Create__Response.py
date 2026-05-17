# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__CF__Create__Response
# Returned by CloudFront__AWS__Client.create_distribution().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Distribution__Status      import Enum__CF__Distribution__Status
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Distribution_Id  import Safe_Str__CF__Distribution_Id
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name      import Safe_Str__CF__Domain_Name


class Schema__CF__Create__Response(Type_Safe):
    distribution_id : Safe_Str__CF__Distribution_Id
    domain_name     : Safe_Str__CF__Domain_Name
    status          : Enum__CF__Distribution__Status = Enum__CF__Distribution__Status.IN_PROGRESS
    message         : str                            = ''
