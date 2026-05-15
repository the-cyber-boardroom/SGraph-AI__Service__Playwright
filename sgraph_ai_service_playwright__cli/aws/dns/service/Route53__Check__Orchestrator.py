# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__Check__Orchestrator
# Thin coordination layer that delegates to the authoritative or public-resolver
# checker depending on which check is requested. Route53__Smart_Verify drives it.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result        import Schema__Dns__Check__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Authoritative__Checker   import Route53__Authoritative__Checker
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Public_Resolver__Checker import Route53__Public_Resolver__Checker


class Route53__Check__Orchestrator(Type_Safe):                                   # Coordinates authoritative and public-resolver checks

    authoritative_checker   : Route53__Authoritative__Checker
    public_resolver_checker : Route53__Public_Resolver__Checker

    def check_authoritative(self, zone_id: str, name: str,
                             rtype: str, expected: str = '') -> Schema__Dns__Check__Result:
        return self.authoritative_checker.check(zone_id, name, rtype, expected)

    def check_public_resolvers(self, name: str, rtype: str,
                                expected: str = '') -> Schema__Dns__Check__Result:
        return self.public_resolver_checker.check(name, rtype, expected)
