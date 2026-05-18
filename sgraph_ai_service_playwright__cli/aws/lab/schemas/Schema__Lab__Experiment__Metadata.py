# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Schema__Lab__Experiment__Metadata
# Static metadata returned by Lab__Experiment.metadata().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Mutation__Tier      import Enum__AWS__Mutation__Tier
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Experiment_Name import Safe_Str__Lab__Experiment_Name


class Schema__Lab__Experiment__Metadata(Type_Safe):
    name        : Safe_Str__Lab__Experiment_Name
    description : str
    tier        : Enum__AWS__Mutation__Tier
    agent       : str                                                              # e.g. "agent-a", "agent-b"
    phase       : str                                                              # e.g. "P0", "P1", "P2"
