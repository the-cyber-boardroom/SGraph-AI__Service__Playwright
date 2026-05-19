# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — List__Schema__VPC__Stack__Ingress_Rule
# Typed list of stack ingress-rule schemas.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Ingress_Rule import Schema__VPC__Stack__Ingress_Rule


class List__Schema__VPC__Stack__Ingress_Rule(Type_Safe__List):
    expected_type = Schema__VPC__Stack__Ingress_Rule
