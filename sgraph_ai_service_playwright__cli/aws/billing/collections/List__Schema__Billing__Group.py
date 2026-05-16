# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Billing__Group
# Ordered list of generic billing groups (forward-compat; used when group_by
# is not SERVICE). Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.billing.schemas.Schema__Billing__Group import Schema__Billing__Group


class List__Schema__Billing__Group(Type_Safe__List):
    expected_type = Schema__Billing__Group
