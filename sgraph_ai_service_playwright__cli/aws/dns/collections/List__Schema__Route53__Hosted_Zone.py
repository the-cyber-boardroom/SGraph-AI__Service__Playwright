# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Route53__Hosted_Zone
# Ordered list of Route 53 hosted zone records. Pure type definition — no
# methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Hosted_Zone import Schema__Route53__Hosted_Zone


class List__Schema__Route53__Hosted_Zone(Type_Safe__List):
    expected_type = Schema__Route53__Hosted_Zone
