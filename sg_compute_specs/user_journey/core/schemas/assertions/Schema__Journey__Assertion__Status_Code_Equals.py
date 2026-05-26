# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Assertion__Status_Code_Equals
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.numerical.safe_int.Safe_Int__Positive                 import Safe_Int__Positive
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url__Path                      import Safe_Str__Url__Path

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Base               import Schema__Journey__Assertion__Base


class Schema__Journey__Assertion__Status_Code_Equals(Schema__Journey__Assertion__Base):  # A captured flow's status equals value
    assertion_type : Enum__Assertion__Type = Enum__Assertion__Type.STATUS_CODE_EQUALS
    expected_status: Safe_Int__Positive                                             # Expected HTTP status code
    url_substring  : Safe_Str__Url__Path = None                                     # Which flow (request URL-path contains); None = first/any
