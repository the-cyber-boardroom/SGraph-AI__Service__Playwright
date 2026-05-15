# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Route53__Record
# One Route 53 resource record set. Alias records populate alias_target and
# use ttl=0 (Route 53 sets TTL on the alias target, not the record itself).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type      import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.primitives.Safe_Str__Record_Name      import Safe_Str__Record_Name
from sgraph_ai_service_playwright__cli.aws.dns.primitives.Safe_Int__TTL              import Safe_Int__TTL


class Schema__Route53__Record(Type_Safe):
    name           : Safe_Str__Record_Name                                            # Record name (FQDN); trailing dot preserved as Route 53 returns it
    record_type    : Enum__Route53__Record_Type                                       # DNS record type (A, CNAME, MX, …)
    ttl            : int                    = 0                                       # TTL in seconds; 0 for alias records (no TTL on the alias itself)
    values         : list                                                             # List of str resource record values; empty for alias records
    alias_target   : str                                                              # Alias target DNS name; empty string when not an alias record
    set_identifier : str                                                              # Routing policy set-id (weighted/latency/geo/…); empty for simple records
