# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__Public_Resolver__Checker
# Fans out dig queries to a curated set of public resolvers and checks whether
# a quorum agree on the expected value.
#
# Two resolver scopes are supported:
#   - smart-verify subset (6 resolvers, default) — used after a mutation by
#     Route53__Smart_Verify to gauge new-name visibility.
#   - full set (8 resolvers) — used by the P1.5 standalone --public-resolvers
#     CLI mode; opt-in only because it pollutes third-party recursive caches.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Check__Mode          import Enum__Dns__Check__Mode
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Resolver             import Enum__Dns__Resolver
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result    import Schema__Dns__Check__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner                   import Dig__Runner

_DEFAULT_QUORUM = 5                                                              # Minimum number of resolvers that must agree for passed=True


class Route53__Public_Resolver__Checker(Type_Safe):                              # Checks a set of public resolvers reach quorum on a record value

    dig_runner : Dig__Runner
    resolvers  : list                                                            # Resolver IPs to query; default = smart-verify subset (6)
    quorum     : int                                                             # Min resolvers that must agree; default 5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.resolvers:
            self.resolvers = [r.value for r in Enum__Dns__Resolver.smart_verify_subset()]
        if not self.quorum:
            self.quorum = _DEFAULT_QUORUM

    def use_full_set(self, quorum: int = 0):                                     # Switch to the 8-resolver full set; optionally override quorum
        self.resolvers = [r.value for r in Enum__Dns__Resolver.full_set()]
        if quorum:
            self.quorum = quorum
        return self

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
        passed = agreed >= self.quorum
        return Schema__Dns__Check__Result(mode         = Enum__Dns__Check__Mode.PUBLIC_RESOLVERS,
                                          name         = name                                   ,
                                          rtype        = rtype                                  ,
                                          expected     = expected                               ,
                                          results      = dig_results                            ,
                                          passed       = passed                                 ,
                                          agreed_count = agreed                                 ,
                                          total_count  = total                                  )
