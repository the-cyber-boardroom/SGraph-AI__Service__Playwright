# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Schema__Lab__Timing__Sample
# One timing observation within an experiment (a single poll result, etc.).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Int__Duration_Ms import Safe_Int__Duration_Ms


class Schema__Lab__Timing__Sample(Type_Safe):
    elapsed_ms  : Safe_Int__Duration_Ms
    label       : str                                                              # human-readable step label, e.g. "resolver-8.8.8.8"
    success     : bool = False
    detail      : str                                                              # extra context (resolver answer, etc.)
