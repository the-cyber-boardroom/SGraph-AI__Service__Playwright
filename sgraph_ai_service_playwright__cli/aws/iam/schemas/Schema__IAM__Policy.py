# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Policy
# One IAM policy document: version + ordered list of statements.
# Pure data. Rendered to JSON by IAM__AWS__Client when writing to AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Statement import List__Schema__IAM__Statement


class Schema__IAM__Policy(Type_Safe):
    version    : str                        = '2012-10-17'
    statements : List__Schema__IAM__Statement
