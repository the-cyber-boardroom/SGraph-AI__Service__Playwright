# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Ec2__Instance__List
# Response envelope for GET /ec2/instances. Carries `region` so callers can
# tell at a glance which region the list applies to, plus a `List__Instance__Info`.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Instance__Info      import Schema__Ec2__Instance__Info
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class List__Ec2__Instance__Info(Type_Safe__List):                                   # Pure type definition
    expected_type = Schema__Ec2__Instance__Info


class Schema__Ec2__Instance__List(Type_Safe):
    region    : Safe_Str__AWS__Region
    instances : List__Ec2__Instance__Info
