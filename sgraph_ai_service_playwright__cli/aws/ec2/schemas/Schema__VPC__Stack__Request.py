# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__VPC__Stack__Request
# Composite request for `sg aws ec2 vpc create-stack`.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str                              import List__Str
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__VPC__Stack__Ingress_Rule    import List__Schema__VPC__Stack__Ingress_Rule


class Schema__VPC__Stack__Request(Type_Safe):
    stack_name          : str                                   = ''
    cidr                : str                                   = '10.0.0.0/16'
    availability_zones  : List__Str                                                  # empty → provisioner picks first 2 AZs from region
    ingress_rules       : List__Schema__VPC__Stack__Ingress_Rule
