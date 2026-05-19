# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Enum__VPC__Stack__Phase
# Ordered phases for the composite VPC-stack provisioner.
# The string values double as the phase display name in the live renderer
# and the JSON report.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__VPC__Stack__Phase(str, Enum):
    VPC                 = 'VPC'
    VPC_ATTRIBUTES      = 'VPC_ATTRIBUTES'
    INTERNET_GATEWAY    = 'INTERNET_GATEWAY'
    IGW_ATTACH          = 'IGW_ATTACH'
    ROUTE_TABLE         = 'ROUTE_TABLE'
    ROUTE_TO_IGW        = 'ROUTE_TO_IGW'
    SUBNETS             = 'SUBNETS'
    SUBNET_ATTRIBUTES   = 'SUBNET_ATTRIBUTES'
    SUBNET_ASSOCIATIONS = 'SUBNET_ASSOCIATIONS'
    SECURITY_GROUP      = 'SECURITY_GROUP'
    SG_INGRESS_RULES    = 'SG_INGRESS_RULES'
    TAG_PROPAGATION     = 'TAG_PROPAGATION'

    def __str__(self):
        return self.value
