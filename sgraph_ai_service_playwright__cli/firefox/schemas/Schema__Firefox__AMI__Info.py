# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__AMI__Info
# Public view of one Firefox AMI. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text


class Schema__Firefox__AMI__Info(Type_Safe):
    ami_id        : Safe_Str__Text                                                  # ami-...
    name          : Safe_Str__Text                                                  # AWS image name
    creation_date : Safe_Str__Text                                                  # ISO-8601
    state         : Safe_Str__Text                                                  # available / pending / failed
    source_stack  : Safe_Str__Text                                                  # sg:stack-name tag
    source_id     : Safe_Str__Text                                                  # sg:source-instance tag
