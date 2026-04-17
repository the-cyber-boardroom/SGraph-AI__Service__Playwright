# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Step Schema Registries + Parsing Helpers (spec §8)
#
# Bridge between the JSON wire format and the typed schemas. Lives in
# `dispatcher/` (not `schemas/`) because registries and parsing are logic.
#
# STEP_SCHEMAS            Enum__Step__Action → Schema__Step__* class (for request parsing)
# STEP_RESULT_SCHEMAS     Enum__Step__Action → Schema__Step__Result__* class (for result building)
# parse_step              Parse one wire-format step dict → typed Schema__Step__* object
# result_schema_for       Get the result schema class for a given action
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                                        import HTTPException

from sgraph_ai_service_playwright.schemas.collections.Dict__Step__Schemas__By_Action                import Dict__Step__Schemas__By_Action
from sgraph_ai_service_playwright.schemas.collections.Dict__Step__Result__Schemas__By_Action        import Dict__Step__Result__Schemas__By_Action
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Step_Id                            import Step_Id
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Evaluate                    import Schema__Step__Result__Evaluate
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Get_Content                 import Schema__Step__Result__Get_Content
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Get_Url                     import Schema__Step__Result__Get_Url
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Click                                 import Schema__Step__Click
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Dispatch_Event                        import Schema__Step__Dispatch_Event
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Evaluate                              import Schema__Step__Evaluate
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Fill                                  import Schema__Step__Fill
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Get_Content                           import Schema__Step__Get_Content
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Get_Url                               import Schema__Step__Get_Url
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Hover                                 import Schema__Step__Hover
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Navigate                              import Schema__Step__Navigate
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Press                                 import Schema__Step__Press
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Screenshot                            import Schema__Step__Screenshot
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Scroll                                import Schema__Step__Scroll
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Select                                import Schema__Step__Select
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Set_Viewport                          import Schema__Step__Set_Viewport
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Video__Start                          import Schema__Step__Video__Start
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Video__Stop                           import Schema__Step__Video__Stop
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Wait_For                              import Schema__Step__Wait_For


# ── Step Input Schema Registry ───────────────────────────────────────────────
STEP_SCHEMAS : Dict__Step__Schemas__By_Action = Dict__Step__Schemas__By_Action({
    Enum__Step__Action.NAVIGATE       : Schema__Step__Navigate      ,
    Enum__Step__Action.CLICK          : Schema__Step__Click         ,
    Enum__Step__Action.FILL           : Schema__Step__Fill          ,
    Enum__Step__Action.PRESS          : Schema__Step__Press         ,
    Enum__Step__Action.SELECT         : Schema__Step__Select        ,
    Enum__Step__Action.HOVER          : Schema__Step__Hover         ,
    Enum__Step__Action.SCROLL         : Schema__Step__Scroll        ,
    Enum__Step__Action.WAIT_FOR       : Schema__Step__Wait_For      ,
    Enum__Step__Action.SCREENSHOT     : Schema__Step__Screenshot    ,
    Enum__Step__Action.VIDEO_START    : Schema__Step__Video__Start  ,
    Enum__Step__Action.VIDEO_STOP     : Schema__Step__Video__Stop   ,
    Enum__Step__Action.EVALUATE       : Schema__Step__Evaluate      ,
    Enum__Step__Action.DISPATCH_EVENT : Schema__Step__Dispatch_Event,
    Enum__Step__Action.SET_VIEWPORT   : Schema__Step__Set_Viewport  ,
    Enum__Step__Action.GET_CONTENT    : Schema__Step__Get_Content   ,
    Enum__Step__Action.GET_URL        : Schema__Step__Get_Url       ,
})


# ── Step Result Schema Registry ──────────────────────────────────────────────
# Actions not listed default to Schema__Step__Result__Base via result_schema_for().
STEP_RESULT_SCHEMAS : Dict__Step__Result__Schemas__By_Action = Dict__Step__Result__Schemas__By_Action({
    Enum__Step__Action.GET_CONTENT : Schema__Step__Result__Get_Content ,
    Enum__Step__Action.GET_URL     : Schema__Step__Result__Get_Url     ,
    Enum__Step__Action.EVALUATE    : Schema__Step__Result__Evaluate    ,
})


# ── Parsing Helpers ──────────────────────────────────────────────────────────
def parse_step(step_dict: dict,                                                     # Parse one step from the wire format
               step_index: int                                                      # Position in sequence for default Step_Id
          ) -> Schema__Step__Base:
    action_str = step_dict.get('action')
    if action_str is None:
        raise HTTPException(422, f"Step at index {step_index} missing required field: action")

    try:
        action = Enum__Step__Action(action_str)                                     # Validates against enum; raises on unknown
    except ValueError:
        raise HTTPException(422, f"Step at index {step_index} has unknown action: {action_str}")

    schema_class = STEP_SCHEMAS.get(action)
    if schema_class is None:
        raise HTTPException(500, f"No schema registered for action: {action_str}")

    step = schema_class.from_json(step_dict)                                        # Type_Safe parses + validates all fields

    if not step.id:                                                                 # Default Step_Id to index if caller omitted
        step.id = Step_Id(str(step_index))

    return step


def result_schema_for(action: Enum__Step__Action) -> type:                          # Get result schema class for an action
    return STEP_RESULT_SCHEMAS.get(action) or Schema__Step__Result__Base
