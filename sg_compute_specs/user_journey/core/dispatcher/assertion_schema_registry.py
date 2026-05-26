# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Assertion Schema Registry + parsing helper
#
# Bridge between the JSON wire format and the typed assertion schemas. Lives in
# `dispatcher/` (not `schemas/`) because the registry + parsing are logic, mirroring
# the substrate's step_schema_registry.
#
# ASSERTION_SCHEMAS   Enum__Assertion__Type → Schema__Journey__Assertion__* class
# parse_assertion     Parse one wire-format assertion dict → typed object
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Base                import Schema__Journey__Assertion__Base
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Http_Header_Present import Schema__Journey__Assertion__Http_Header_Present
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Selector_Text_Contains import Schema__Journey__Assertion__Selector_Text_Contains
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Selector_Text_Equals import Schema__Journey__Assertion__Selector_Text_Equals
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Selector_Visible    import Schema__Journey__Assertion__Selector_Visible
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Status_Code_Equals  import Schema__Journey__Assertion__Status_Code_Equals
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Url_Contains        import Schema__Journey__Assertion__Url_Contains
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Url_Equals          import Schema__Journey__Assertion__Url_Equals
from sg_compute_specs.user_journey.core.schemas.collections.Dict__Assertion__Schemas__By_Type              import Dict__Assertion__Schemas__By_Type
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                                import Enum__Assertion__Type


# ── Assertion Schema Registry ────────────────────────────────────────────────
ASSERTION_SCHEMAS : Dict__Assertion__Schemas__By_Type = Dict__Assertion__Schemas__By_Type({
    Enum__Assertion__Type.URL_CONTAINS           : Schema__Journey__Assertion__Url_Contains          ,
    Enum__Assertion__Type.URL_EQUALS             : Schema__Journey__Assertion__Url_Equals            ,
    Enum__Assertion__Type.SELECTOR_VISIBLE       : Schema__Journey__Assertion__Selector_Visible      ,
    Enum__Assertion__Type.SELECTOR_TEXT_EQUALS   : Schema__Journey__Assertion__Selector_Text_Equals  ,
    Enum__Assertion__Type.SELECTOR_TEXT_CONTAINS : Schema__Journey__Assertion__Selector_Text_Contains,
    Enum__Assertion__Type.STATUS_CODE_EQUALS     : Schema__Journey__Assertion__Status_Code_Equals    ,
    Enum__Assertion__Type.HTTP_HEADER_PRESENT    : Schema__Journey__Assertion__Http_Header_Present   ,
})


def parse_assertion(assertion_dict: dict) -> Schema__Journey__Assertion__Base:      # Parse one assertion from the wire format
    type_str = assertion_dict.get('assertion_type')
    if type_str is None:
        raise ValueError("Assertion missing required field: assertion_type")

    try:
        assertion_type = Enum__Assertion__Type(type_str)                            # Validates against enum; raises on unknown
    except ValueError:
        raise ValueError(f"Unknown assertion_type: {type_str}")

    schema_class = ASSERTION_SCHEMAS.get(assertion_type)
    if schema_class is None:
        raise ValueError(f"No schema registered for assertion_type: {type_str}")

    return schema_class.from_json(assertion_dict)                                   # Type_Safe parses + validates all fields
