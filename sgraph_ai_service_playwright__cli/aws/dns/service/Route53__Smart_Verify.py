# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__Smart_Verify
# Decides which post-mutation checks to run based on whether the record was
# new, updated, or deleted. Encodes the TTL-cache safety reasoning so the
# CLI can print the verbatim info lines from the spec.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type       import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Smart_Verify__Decision     import Enum__Smart_Verify__Decision
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Smart_Verify__Decision import Schema__Smart_Verify__Decision
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Smart_Verify__Result   import Schema__Smart_Verify__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client           import Route53__AWS__Client
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Check__Orchestrator   import Route53__Check__Orchestrator

_MSG_NEW_NAME = (                                                                # Verbatim info line for the NEW_NAME path
    'Auto-verify: new name — no prior recursive cache to pollute, so the '
    'authoritative check AND a curated 6-resolver EU+US public-resolver check '
    'are both run. Safe by construction.'
)


class Route53__Smart_Verify(Type_Safe):                                          # Decides and runs the right post-mutation verification checks

    r53_client  : Route53__AWS__Client
    orchestrator: Route53__Check__Orchestrator

    def decide_before_add(self, zone_id: str, name: str,
                          rtype: Enum__Route53__Record_Type) -> Schema__Smart_Verify__Decision:  # Inspect current state; return NEW_NAME or UPSERT
        existing = self.r53_client.get_record(zone_id, name, rtype)
        if existing is None:
            return Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.NEW_NAME,
                                                  prior_ttl   = 0                                   ,
                                                  prior_values= []                                   )
        return Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.UPSERT  ,
                                              prior_ttl   = int(existing.ttl)                    ,
                                              prior_values= list(existing.values)                )

    def verify_after_mutation(self, decision      : Schema__Smart_Verify__Decision,
                               zone_id            : str                           ,
                               name               : str                           ,
                               rtype              : str                           ,
                               expected           : str = ''                      ) -> Schema__Smart_Verify__Result:
        auth_result = self.orchestrator.check_authoritative(zone_id, name, rtype, expected)

        if decision.decision == Enum__Smart_Verify__Decision.NEW_NAME:
            pub_result   = self.orchestrator.check_public_resolvers(name, rtype, expected)
            return Schema__Smart_Verify__Result(decision        = decision.decision,
                                                authoritative   = auth_result      ,
                                                public_resolvers= pub_result       ,
                                                skipped_public  = False            ,
                                                skip_message    = ''               )

        if decision.decision == Enum__Smart_Verify__Decision.UPSERT:
            prior_ttl   = decision.prior_ttl
            skip_msg    = (
                f"Authoritative is consistent. Public-resolver check skipped — "
                f"would risk locking in stale answers for the remaining ~{prior_ttl}s "
                f"of the prior record's TTL. Run 'sg aws dns records check {name} "
                f"--public-resolvers' once the old TTL has elapsed."
            )
            return Schema__Smart_Verify__Result(decision        = decision.decision,
                                                authoritative   = auth_result      ,
                                                public_resolvers= None             ,
                                                skipped_public  = True             ,
                                                skip_message    = skip_msg         )

        # DELETE path
        prior_ttl = decision.prior_ttl
        skip_msg  = (
            f"Authoritative confirms deletion. Public-resolver check skipped — "
            f"recursives may still serve the cached positive answer for up to ~{prior_ttl}s. "
            f"Run 'sg aws dns records check {name} --public-resolvers' after that to confirm propagation."
        )
        return Schema__Smart_Verify__Result(decision        = decision.decision,
                                            authoritative   = auth_result      ,
                                            public_resolvers= None             ,
                                            skipped_public  = True             ,
                                            skip_message    = skip_msg         )
