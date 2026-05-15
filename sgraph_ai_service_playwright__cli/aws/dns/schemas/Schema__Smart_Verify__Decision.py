# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Smart_Verify__Decision
# Decision made by Route53__Smart_Verify before a record mutation, based on
# whether the name+type already existed. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Smart_Verify__Decision    import Enum__Smart_Verify__Decision


class Schema__Smart_Verify__Decision(Type_Safe):
    decision     : Enum__Smart_Verify__Decision                                       # NEW_NAME | UPSERT | DELETE
    prior_ttl    : int                                                                # 0 if NEW_NAME; TTL of the pre-existing record otherwise
    prior_values : list                                                               # Empty if NEW_NAME; list of str values of the pre-existing record
