# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Assertion__Base
#
# Base for every assertion. `assertion_type` is the discriminator — each subclass
# MUST set a default matching its Enum__Assertion__Type variant. Parsed from the
# wire via the assertion_schema_registry (mirrors the step dispatcher pattern).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Assertion_Id                     import Assertion_Id


class Schema__Journey__Assertion__Base(Type_Safe):                                  # Fields common to every assertion
    assertion_type : Enum__Assertion__Type                                          # Discriminator — set by each subclass
    assertion_id   : Assertion_Id = None                                            # Caller-supplied; optional
