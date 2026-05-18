# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — Schema__CloudTrail__Event
# Summary schema for a single CloudTrail event.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region          import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__Error_Code    import Safe_Str__CloudTrail__Error_Code
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__Error_Message import Safe_Str__CloudTrail__Error_Message
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__Event_Id      import Safe_Str__CloudTrail__Event_Id
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__Event_Name    import Safe_Str__CloudTrail__Event_Name
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__Event_Time    import Safe_Str__CloudTrail__Event_Time
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__IP_Address    import Safe_Str__CloudTrail__IP_Address
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__Json_Blob     import Safe_Str__CloudTrail__Json_Blob
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__Username      import Safe_Str__CloudTrail__Username


class Schema__CloudTrail__Event(Type_Safe):
    event_id             : Safe_Str__CloudTrail__Event_Id
    event_time           : Safe_Str__CloudTrail__Event_Time
    event_name           : Safe_Str__CloudTrail__Event_Name
    username             : Safe_Str__CloudTrail__Username
    source_ip_address    : Safe_Str__CloudTrail__IP_Address
    aws_region           : Safe_Str__AWS__Region
    request_parameters   : Safe_Str__CloudTrail__Json_Blob     # JSON-serialised string
    response_elements    : Safe_Str__CloudTrail__Json_Blob     # JSON-serialised string
    resources            : Safe_Str__CloudTrail__Json_Blob     # JSON-serialised string
    error_code           : Safe_Str__CloudTrail__Error_Code
    error_message        : Safe_Str__CloudTrail__Error_Message
