# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__IAM__Policy
# Ordered list of IAM policies (inline policies on a role). Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List              import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Policy         import Schema__IAM__Policy


class List__Schema__IAM__Policy(Type_Safe__List):
    expected_type = Schema__IAM__Policy
