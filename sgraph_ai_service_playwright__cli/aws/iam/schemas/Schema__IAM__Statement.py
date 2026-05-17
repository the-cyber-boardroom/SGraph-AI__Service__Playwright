# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Statement
# One IAM policy statement. Pure data with a documented least-privilege contract:
#
#   • actions — typed as List__Safe_Str__Aws__Action; bare "*" structurally
#     rejected (Safe_Str__Aws__Action regex requires a service prefix colon).
#   • resources — "* " requires allow_wildcard_resource=True; default False.
#     Callers that omit the flag leave the auditor to flag it at WARN/CRITICAL.
#   • condition_json — JSON string; empty string means no Condition block.
#     Power actions (iam:PassRole, ec2:Start*, ec2:Stop*, ec2:Terminate*,
#     lambda:Invoke*) without a condition are flagged CRITICAL by the auditor.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Action   import List__Safe_Str__Aws__Action
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Resource import List__Safe_Str__Aws__Resource


class Schema__IAM__Statement(Type_Safe):
    effect                 : str                        = 'Allow'  # 'Allow' | 'Deny'
    actions                : List__Safe_Str__Aws__Action             # no bare "*"
    resources              : List__Safe_Str__Aws__Resource           # ARNs or "*"
    allow_wildcard_resource: bool                       = False     # explicit opt-in for Resource: "*"
    condition_json         : str                        = ''        # JSON; empty = no Condition block
