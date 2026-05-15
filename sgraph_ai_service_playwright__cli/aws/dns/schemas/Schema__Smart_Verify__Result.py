# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Smart_Verify__Result
# Full result of the smart-verify post-mutation check — authoritative always
# run; public-resolver check skipped on UPSERT/DELETE paths.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                          import Optional

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Smart_Verify__Decision    import Enum__Smart_Verify__Decision
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result    import Schema__Dns__Check__Result


class Schema__Smart_Verify__Result(Type_Safe):
    decision         : Enum__Smart_Verify__Decision                                   # Decision that drove which checks were run
    authoritative    : Schema__Dns__Check__Result                                     # Result of the authoritative NS check (always present)
    public_resolvers : Optional[Schema__Dns__Check__Result]  = None                  # Present for NEW_NAME path; None for UPSERT/DELETE
    skipped_public   : bool                                                           # True when public-resolver check was skipped
    skip_message     : str                                                            # The verbatim info line printed to the user (empty for NEW_NAME)
