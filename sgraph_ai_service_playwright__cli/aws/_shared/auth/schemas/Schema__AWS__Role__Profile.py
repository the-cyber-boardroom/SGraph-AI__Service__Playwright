# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: Schema__AWS__Role__Profile
# The least-privilege intent of one command family (e.g. el-lets-cf): the IAM role we
# assume/create for it and the policy statements that role carries. ONE source of
# truth read by both the role-creator (`… iam create`) and the transparent assumer, so
# "what we grant" and "what we assume" never drift. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                  import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.List__AWS__Policy__Statement import List__AWS__Policy__Statement
from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str                     import List__Str


class Schema__AWS__Role__Profile(Type_Safe):
    family         : str                                                             # stable id, e.g. 'el-lets-cf'
    role_name      : str                                                             # the IAM role to assume / create, e.g. 'sg-lets-cf'
    description    : str
    statements     : List__AWS__Policy__Statement
    trust_services : List__Str                                                       # when set, an execution-role trust for these AWS service
                                                                                     # principals (e.g. lambda + edgelambda) instead of account-root assume
