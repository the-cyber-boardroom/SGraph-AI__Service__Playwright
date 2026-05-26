# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Assertion__Url_Contains
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url__Path                      import Safe_Str__Url__Path

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Base               import Schema__Journey__Assertion__Base


class Schema__Journey__Assertion__Url_Contains(Schema__Journey__Assertion__Base):   # Terminal URL contains substring
    assertion_type : Enum__Assertion__Type = Enum__Assertion__Type.URL_CONTAINS
    expected       : Safe_Str__Url__Path                                            # URL-path substring the terminal URL must contain
