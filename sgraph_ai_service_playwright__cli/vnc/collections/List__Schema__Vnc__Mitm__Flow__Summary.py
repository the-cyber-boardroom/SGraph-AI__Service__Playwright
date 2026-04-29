# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Vnc__Mitm__Flow__Summary
# Type_Safe__List for the flow-summary listing. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Mitm__Flow__Summary import Schema__Vnc__Mitm__Flow__Summary


class List__Schema__Vnc__Mitm__Flow__Summary(Type_Safe__List):
    expected_type = Schema__Vnc__Mitm__Flow__Summary
