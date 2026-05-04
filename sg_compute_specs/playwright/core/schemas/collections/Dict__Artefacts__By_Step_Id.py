# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Dict__Artefacts__By_Step_Id (spec §6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict                               import Type_Safe__Dict

from sg_compute_specs.playwright.core.schemas.collections.List__Artefact__Refs                          import List__Artefact__Refs
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Step_Id                            import Step_Id


class Dict__Artefacts__By_Step_Id(Type_Safe__Dict):                                 # Artefacts grouped by producing step
    expected_key_type   = Step_Id
    expected_value_type = List__Artefact__Refs
