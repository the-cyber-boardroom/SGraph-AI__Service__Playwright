# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__AMI__Info
# Public view of one ephemeral elastic AMI. Pure data — populated from the
# describe_images response by Elastic__AWS__Client.list_elastic_amis.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text


class Schema__Elastic__AMI__Info(Type_Safe):
    ami_id        : Safe_Str__Text                                                  # ami-...
    name          : Safe_Str__Text                                                  # AWS image name
    description   : Safe_Str__Text
    creation_date : Safe_Str__Text                                                  # ISO-8601 string Kibana-emitted (preserved verbatim)
    state         : Safe_Str__Text                                                  # available / pending / failed / ...
    source_stack  : Safe_Str__Text                                                  # sg:stack-name tag value
    source_id     : Safe_Str__Text                                                  # sg:source-instance tag value (the instance the AMI was baked from)
