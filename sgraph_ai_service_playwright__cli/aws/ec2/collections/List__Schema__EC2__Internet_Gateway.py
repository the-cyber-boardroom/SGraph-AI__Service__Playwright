# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — List__Schema__EC2__Internet_Gateway
# Typed list of EC2 Internet Gateway schemas.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Internet_Gateway import Schema__EC2__Internet_Gateway


class List__Schema__EC2__Internet_Gateway(Type_Safe__List):
    expected_type = Schema__EC2__Internet_Gateway
