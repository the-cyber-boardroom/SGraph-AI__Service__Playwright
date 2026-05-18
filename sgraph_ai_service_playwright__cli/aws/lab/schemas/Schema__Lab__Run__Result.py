# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Schema__Lab__Run__Result
# Returned by Lab__Experiment.execute() — captures outcome + timings.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Experiment__Status  import Enum__Lab__Experiment__Status
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Int__Duration_Ms     import Safe_Int__Duration_Ms
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Run_Id     import Safe_Str__Lab__Run_Id
from sgraph_ai_service_playwright__cli.aws.lab.collections.List__Schema__Lab__Timing__Sample import List__Schema__Lab__Timing__Sample


class Schema__Lab__Run__Result(Type_Safe):
    run_id      : Safe_Str__Lab__Run_Id
    status      : Enum__Lab__Experiment__Status
    started_at  : str                                                              # ISO-8601
    finished_at : str                                                              # ISO-8601
    duration_ms : Safe_Int__Duration_Ms
    samples     : List__Schema__Lab__Timing__Sample
    error       : str                                                              # set on FAILED/TIMEOUT/ABORTED
    notes       : str                                                              # free-form summary
