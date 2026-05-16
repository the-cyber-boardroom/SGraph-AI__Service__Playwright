# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Billing__Line_Item
# Ordered list of cost line items within a daily bucket. Pure type definition —
# no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.billing.schemas.Schema__Billing__Line_Item import Schema__Billing__Line_Item


class List__Schema__Billing__Line_Item(Type_Safe__List):
    expected_type = Schema__Billing__Line_Item
