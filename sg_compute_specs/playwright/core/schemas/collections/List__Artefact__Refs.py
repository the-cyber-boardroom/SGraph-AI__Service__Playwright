# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — List__Artefact__Refs (spec §6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List                               import Type_Safe__List

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref


class List__Artefact__Refs(Type_Safe__List):
    expected_type = Schema__Artefact__Ref
