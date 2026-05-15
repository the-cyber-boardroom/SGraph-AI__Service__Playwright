# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__Local__Checker
# Runs a single dig query through the host's default resolver (whatever
# /etc/resolv.conf or the platform resolver config points at). Used by the
# P1.5 `sg aws dns records check --local` mode.
#
# WARNING: this is cache-polluting. The upstream resolver (often a corporate
# proxy or VPN resolver) WILL cache the answer for up to the record's TTL.
# Opt-in only — never invoked by smart-verify.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Check__Mode          import Enum__Dns__Check__Mode
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result    import Schema__Dns__Check__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner                   import Dig__Runner


class Route53__Local__Checker(Type_Safe):                                        # Single-shot dig through the host's default resolver

    dig_runner : Dig__Runner

    def check(self, name: str, rtype: str,
              expected: str = '') -> Schema__Dns__Check__Result:                 # Run dig with no @<ns> arg; build a single-row result
        result      = self.dig_runner.run(nameserver='', name=name, rtype=rtype, no_recurse=False)
        if expected:
            passed = expected in result.values
        else:
            passed = bool(result.values)
        agreed = 1 if passed else 0
        return Schema__Dns__Check__Result(mode         = Enum__Dns__Check__Mode.LOCAL,
                                          name         = name                        ,
                                          rtype        = rtype                       ,
                                          expected     = expected                    ,
                                          results      = [result]                    ,
                                          passed       = passed                      ,
                                          agreed_count = agreed                      ,
                                          total_count  = 1                           )
