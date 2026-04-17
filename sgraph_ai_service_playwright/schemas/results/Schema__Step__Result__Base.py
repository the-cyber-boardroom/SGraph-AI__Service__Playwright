# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Result__Base (spec §5.7)
#
# Common fields for every step result. Dispatcher selects a typed subclass
# for get_content / get_url / evaluate; all others use this base directly.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                                  import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Step_Id                            import Step_Id
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds


class Schema__Step__Result__Base(Type_Safe):                                        # Common fields for every step result
    step_id             : Step_Id
    step_index          : Safe_UInt                                                 # Position in sequence (0-based)
    action              : Enum__Step__Action
    status              : Enum__Step__Status
    duration_ms         : Safe_UInt__Milliseconds
    error_message       : Safe_Str__Text = None                                     # Populated on failure
    artefacts           : List[Schema__Artefact__Ref]                               # Artefacts produced by this step
