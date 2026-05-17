# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Schema__Creds__Export
# Temporary credentials ready for export to the shell or downstream tooling.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region             import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Access_Key_Id      import Safe_Str__Creds__Access_Key_Id
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Secret_Access_Key  import Safe_Str__Creds__Secret_Access_Key
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Session_Token      import Safe_Str__Creds__Session_Token
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Timestamp          import Safe_Str__Creds__Timestamp


class Schema__Creds__Export(Type_Safe):
    access_key_id     : Safe_Str__Creds__Access_Key_Id
    secret_access_key : Safe_Str__Creds__Secret_Access_Key
    session_token     : Safe_Str__Creds__Session_Token
    expiration        : Safe_Str__Creds__Timestamp
    region            : Safe_Str__AWS__Region
