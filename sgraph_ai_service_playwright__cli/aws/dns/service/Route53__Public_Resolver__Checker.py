# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__Public_Resolver__Checker
# Fans out dig queries to a curated set of public resolvers and checks whether
# a quorum (5/6) agree on the expected value.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Check__Mode          import Enum__Dns__Check__Mode
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Resolver             import Enum__Dns__Resolver
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result    import Schema__Dns__Check__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner                   import Dig__Runner

_CURATED_RESOLVERS = [                                                           # The 6 curated resolvers for smart-verify new-name checks
    Enum__Dns__Resolver.CLOUDFLARE_1.value,
    Enum__Dns__Resolver.CLOUDFLARE_2.value,
    Enum__Dns__Resolver.GOOGLE_1.value    ,
    Enum__Dns__Resolver.GOOGLE_2.value    ,
    Enum__Dns__Resolver.QUAD9.value       ,
    Enum__Dns__Resolver.ADGUARD_EU.value  ,
]

_QUORUM = 5                                                                      # Minimum number of resolvers that must agree for passed=True


class Route53__Public_Resolver__Checker(Type_Safe):                              # Checks a set of public resolvers reach quorum on a record value

    dig_runner : Dig__Runner
    resolvers  : list                                                            # Default = the 6 curated resolvers; override in tests

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.resolvers:
            self.resolvers = list(_CURATED_RESOLVERS)

    def check(self, name: str, rtype: str,
              expected: str = '') -> Schema__Dns__Check__Result:                 # Fan out dig to each resolver; passed when quorum agree on expected
        dig_results = []
        agreed      = 0
        for resolver_ip in self.resolvers:
            result = self.dig_runner.run(resolver_ip, name, rtype)
            dig_results.append(result)
            if expected:
                if expected in result.values:
                    agreed += 1
            else:
                if result.values:
                    agreed += 1
        total  = len(self.resolvers)
        passed = agreed >= _QUORUM
        return Schema__Dns__Check__Result(mode         = Enum__Dns__Check__Mode.PUBLIC_RESOLVERS,
                                          name         = name                                   ,
                                          rtype        = rtype                                  ,
                                          expected     = expected                               ,
                                          results      = dig_results                            ,
                                          passed       = passed                                 ,
                                          agreed_count = agreed                                 ,
                                          total_count  = total                                  )
