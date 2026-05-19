# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__VPC__Stack__Report
# Outcome of a VPC stack create / delete operation.
# Includes per-phase timing records and the final resource id set so the CLI
# can render both a summary table and the auto-resolve-friendly JSON shape.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Schema__AWS__Phase__Result import List__Schema__AWS__Phase__Result
from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str                        import List__Str


class Schema__VPC__Stack__Report(Type_Safe):
    operation           : str  = ''                                       # 'create' | 'delete'
    stack_name          : str  = ''
    ok                  : bool = False
    total_ms            : int  = 0
    vpc_id              : str  = ''
    internet_gateway_id : str  = ''
    route_table_id      : str  = ''
    security_group_id   : str  = ''
    subnet_ids          : List__Str
    phases              : List__Schema__AWS__Phase__Result
    error               : str  = ''
    rollback_errors     : List__Str
