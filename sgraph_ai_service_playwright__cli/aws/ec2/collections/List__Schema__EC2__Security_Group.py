# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — List__Schema__EC2__Security_Group
# Typed list of full EC2 security-group schemas (sg sub-app).
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Security_Group import Schema__EC2__Security_Group


class List__Schema__EC2__Security_Group(Type_Safe__List):
    expected_type = Schema__EC2__Security_Group
