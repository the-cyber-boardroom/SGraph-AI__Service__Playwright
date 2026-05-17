# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Audit__Report
# Output of IAM__Policy__Auditor.audit(). Pure data.
# overall_severity = max(finding.severity for finding in findings), or INFO when
# there are no findings. CLI exit codes: 0 = clean, 1 = WARN, 2 = CRITICAL.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Audit__Finding import List__Schema__IAM__Audit__Finding
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Severity             import Enum__IAM__Audit__Severity
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name          import Safe_Str__IAM__Role_Name


class Schema__IAM__Audit__Report(Type_Safe):
    role_name        : Safe_Str__IAM__Role_Name
    findings         : List__Schema__IAM__Audit__Finding
    overall_severity : Enum__IAM__Audit__Severity = Enum__IAM__Audit__Severity.INFO
    passed_count     : int                        = 0
    failed_count     : int                        = 0
