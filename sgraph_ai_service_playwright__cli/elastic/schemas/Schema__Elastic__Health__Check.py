# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Health__Check
# One row in the `sp elastic health` output: a named check with a status and
# a short diagnostic line. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Health__Status           import Enum__Health__Status
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Diagnostic      import Safe_Str__Diagnostic


class Schema__Elastic__Health__Check(Type_Safe):
    name    : Safe_Str__Text                                                        # Short identifier rendered in the first column (e.g. "tcp-443")
    status  : Enum__Health__Status      = Enum__Health__Status.SKIP
    detail  : Safe_Str__Diagnostic                                                  # Free-form one-liner — what happened or what to do about it
