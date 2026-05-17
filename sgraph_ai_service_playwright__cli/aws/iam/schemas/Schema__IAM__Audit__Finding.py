# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Audit__Finding
# One finding emitted by IAM__Policy__Auditor. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Finding     import Enum__IAM__Audit__Finding
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Severity    import Enum__IAM__Audit__Severity


class Schema__IAM__Audit__Finding(Type_Safe):
    severity          : Enum__IAM__Audit__Severity = Enum__IAM__Audit__Severity.INFO
    code              : Enum__IAM__Audit__Finding  = Enum__IAM__Audit__Finding.WILDCARD_ACTION
    statement_index   : int                        = -1    # -1 = whole-role finding
    message           : str                        = ''
    remediation_hint  : str                        = ''
