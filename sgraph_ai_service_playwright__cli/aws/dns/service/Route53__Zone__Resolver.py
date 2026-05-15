# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__Zone__Resolver
# Resolves a fully-qualified domain name to the deepest hosted zone owned by
# the account. Walks the FQDN labels longest-first until a match is found.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                          import Optional

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Hosted_Zone  import Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client          import Route53__AWS__Client


class Route53__Zone__Resolver(Type_Safe):                                        # Walks FQDN labels to find the deepest owned zone

    r53_client  : Route53__AWS__Client
    _zone_cache : list                                                           # Cached list of all zones — populated on first call

    def resolve_zone_for_fqdn(self, fqdn: str) -> Schema__Route53__Hosted_Zone:  # Returns the deepest hosted zone that owns fqdn; raises ValueError if none
        if not self._zone_cache:
            self._zone_cache = list(self.r53_client.list_hosted_zones())
        zone_names = {str(z.name).rstrip('.'): z for z in self._zone_cache}
        parts = fqdn.rstrip('.').split('.')
        # Walk deepest candidate first — start with the FQDN itself, then strip leading labels.
        # This is required for the case where the FQDN IS itself a zone apex (e.g. NS / SOA
        # queries for sg-compute.sgraph.ai must target the child zone's NS, not the parent's).
        for i in range(len(parts) - 1):
            candidate = '.'.join(parts[i:])
            if candidate in zone_names:
                return zone_names[candidate]
        raise ValueError(f"No hosted zone in account owns '{fqdn}'")
