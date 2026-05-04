# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Mitm__Status
# Response for GET /firefox/{stack_id}/mitm/status.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text            import Safe_Str__Text

from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Mitm__Mode                   import Enum__Mitm__Mode
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime           import Safe_Str__ISO_Datetime
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Vault__Handle          import Safe_Str__Vault__Handle


class Schema__Firefox__Mitm__Status(Type_Safe):
    enabled         : bool               = False
    mode            : Enum__Mitm__Mode   = Enum__Mitm__Mode.PASSTHROUGH
    script_handle   : Safe_Str__Vault__Handle                                    # empty = no script uploaded
    last_request_at : Safe_Str__ISO_Datetime                                     # empty = no traffic recorded yet
    script_url      : Safe_Str__Text                                             # mitmweb UI URL
