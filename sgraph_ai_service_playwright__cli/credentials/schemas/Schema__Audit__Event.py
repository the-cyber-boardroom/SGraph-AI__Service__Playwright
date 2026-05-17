# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Schema__Audit__Event
# One line in ~/.sg/audit.jsonl.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Audit__Action                  import Enum__Audit__Action
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Audit__Detail         import Safe_Str__Audit__Detail
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name             import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime                 import Safe_Str__ISO_Datetime


class Schema__Audit__Event(Type_Safe):
    timestamp       : Safe_Str__ISO_Datetime
    action          : Enum__Audit__Action
    role            : Safe_Str__Role__Name      # role context (may be empty)
    detail          : Safe_Str__Audit__Detail   # free-form one-liner — never contains secret values
