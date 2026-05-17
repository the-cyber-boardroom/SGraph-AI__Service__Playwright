# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__IAM__Audit__Finding
# Ordered list of audit findings from IAM__Policy__Auditor. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List              import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Audit__Finding import Schema__IAM__Audit__Finding


class List__Schema__IAM__Audit__Finding(Type_Safe__List):
    expected_type = Schema__IAM__Audit__Finding
