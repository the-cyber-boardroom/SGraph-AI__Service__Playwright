# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__VPC__Stack__Detail
# Snapshot of the resources currently owned by a named stack.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str import List__Str


class Schema__VPC__Stack__Detail(Type_Safe):
    stack_name          : str       = ''
    vpc_id              : str       = ''
    internet_gateway_id : str       = ''
    route_table_id      : str       = ''
    security_group_id   : str       = ''
    subnet_ids          : List__Str
