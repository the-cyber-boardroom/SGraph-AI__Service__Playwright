# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__ACM__Certificate
# Summary view of one ACM certificate as returned by list_certificates +
# describe_certificate. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.acm.enums.Enum__ACM__Cert_Status          import Enum__ACM__Cert_Status
from sgraph_ai_service_playwright__cli.aws.acm.enums.Enum__ACM__Cert_Type            import Enum__ACM__Cert_Type
from sgraph_ai_service_playwright__cli.aws.dns.primitives.Safe_Str__Domain_Name      import Safe_Str__Domain_Name


class Schema__ACM__Certificate(Type_Safe):
    arn              : str                                                             # Full ACM certificate ARN
    domain_name      : Safe_Str__Domain_Name                                          # Primary domain name (DomainName field)
    san_count        : int                                                             # Count of subject alternative names (excluding the primary domain)
    status           : Enum__ACM__Cert_Status                                         # Certificate lifecycle status
    cert_type        : Enum__ACM__Cert_Type                                           # Certificate origin type
    in_use_by        : int                                                             # Count of AWS resources using this certificate
    renewal_eligible : bool                                                            # True when ACM reports the cert as eligible for managed renewal
    region           : str                                                             # AWS region where the cert lives (auto-detected from ARN)
