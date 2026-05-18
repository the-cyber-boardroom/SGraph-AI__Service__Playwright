# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Schema__Lab__Ledger__Entry
# One created-resource record written to the JSONL ledger.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN     import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region  import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Entry__State         import Enum__Lab__Entry__State
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type        import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Entry_Id    import Safe_Str__Lab__Entry_Id
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Run_Id      import Safe_Str__Lab__Run_Id


class Schema__Lab__Ledger__Entry(Type_Safe):
    entry_id      : Safe_Str__Lab__Entry_Id
    run_id        : Safe_Str__Lab__Run_Id
    resource_type : Enum__Lab__Resource_Type
    resource_id   : Safe_Str__AWS__ARN                                             # ARN or composite key (e.g. zone-id/name/type)
    region        : Safe_Str__AWS__Region
    created_at    : str                                                            # ISO-8601; str is allowed in non-identity schemas
    expires_at    : str                                                            # ISO-8601 TTL used by sweeper
    state         : Enum__Lab__Entry__State
    experiment    : str                                                            # experiment name, free-form label
    extra         : str                                                            # JSON blob for resource-specific extra context
