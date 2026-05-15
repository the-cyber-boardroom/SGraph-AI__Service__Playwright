# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__Authoritative__Checker
# Checks DNS consistency across all authoritative nameservers for a zone.
# Gets the NS set from Route53 GetHostedZone → DelegationSet.NameServers (the
# definitive list Route 53 provides), then fans out dig +norecurse to each NS.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Check__Mode          import Enum__Dns__Check__Mode
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result    import Schema__Dns__Check__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner                   import Dig__Runner
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client          import Route53__AWS__Client


class Route53__Authoritative__Checker(Type_Safe):                                # Checks all authoritative NS servers for a zone agree on a record

    dig_runner  : Dig__Runner
    r53_client  : Route53__AWS__Client

    def get_ns_for_zone(self, zone_id: str) -> list:                             # Calls GetHostedZone and extracts NS from DelegationSet.NameServers
        r53  = self.r53_client.client()
        resp = r53.get_hosted_zone(Id=zone_id)
        ns_list = resp.get('DelegationSet', {}).get('NameServers', [])
        return [ns.rstrip('.') for ns in ns_list]                               # Strip trailing dots before returning

    def check(self, zone_id: str, name: str, rtype: str,
              expected: str = '') -> Schema__Dns__Check__Result:                 # Fan out dig +norecurse to each NS; build aggregated result
        ns_servers  = self.get_ns_for_zone(zone_id)
        dig_results = []
        agreed      = 0
        for ns in ns_servers:
            result = self.dig_runner.run(ns, name, rtype, no_recurse=True)
            dig_results.append(result)
            if expected:
                if expected in result.values:
                    agreed += 1
            else:
                if result.values:                                                # No expected value — just check it resolves to something
                    agreed += 1
        total  = len(ns_servers)
        passed = (agreed == total) if total > 0 else False
        return Schema__Dns__Check__Result(mode         = Enum__Dns__Check__Mode.AUTHORITATIVE,
                                          name         = name                                ,
                                          rtype        = rtype                               ,
                                          expected     = expected                            ,
                                          results      = dig_results                         ,
                                          passed       = passed                              ,
                                          agreed_count = agreed                              ,
                                          total_count  = total                               )
