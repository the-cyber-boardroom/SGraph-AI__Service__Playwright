# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__CF__Origin
# One CloudFront origin entry. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Origin__Protocol         import Enum__CF__Origin__Protocol
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name     import Safe_Str__CF__Domain_Name
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Origin_Id       import Safe_Str__CF__Origin_Id


class Schema__CF__Origin(Type_Safe):
    origin_id     : Safe_Str__CF__Origin_Id                                               # Logical origin identifier (unique within distribution)
    domain_name   : Safe_Str__CF__Domain_Name                                             # Hostname of the origin (no scheme)
    protocol      : Enum__CF__Origin__Protocol = Enum__CF__Origin__Protocol.HTTPS_ONLY   # Origin-facing protocol
    https_port    : int                        = 443
