# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Route53__Hosted_Zone
# One Route 53 hosted zone as returned by list_hosted_zones / get_hosted_zone.
# Pure data — no methods. Trailing dots are stripped from name before storage.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.primitives.Safe_Str__Domain_Name     import Safe_Str__Domain_Name
from sgraph_ai_service_playwright__cli.aws.dns.primitives.Safe_Str__Hosted_Zone_Id  import Safe_Str__Hosted_Zone_Id


class Schema__Route53__Hosted_Zone(Type_Safe):
    zone_id          : Safe_Str__Hosted_Zone_Id                                       # Bare zone id (Z + alphanumeric); no /hostedzone/ prefix
    name             : Safe_Str__Domain_Name                                          # Zone apex name; trailing dot stripped by client before storage
    private_zone     : bool                                                           # True for VPC-attached private zones
    record_count     : int                                                            # ResourceRecordSetCount from Route 53
    comment          : str                                                            # HostedZoneConfig.Comment (empty string when absent)
    caller_reference : str                                                            # CallerReference — opaque AWS string
