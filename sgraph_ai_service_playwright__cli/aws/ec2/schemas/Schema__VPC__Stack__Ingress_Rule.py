# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__VPC__Stack__Ingress_Rule
# Single ingress rule to apply during the SG_INGRESS_RULES phase.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__VPC__Stack__Ingress_Rule(Type_Safe):
    protocol   : str = 'tcp'
    from_port  : int = 0
    to_port    : int = 0
    cidr_block : str = '0.0.0.0/0'
