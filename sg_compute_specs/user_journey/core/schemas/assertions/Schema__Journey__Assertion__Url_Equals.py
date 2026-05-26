# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Assertion__Url_Equals
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Base               import Schema__Journey__Assertion__Base


class Schema__Journey__Assertion__Url_Equals(Schema__Journey__Assertion__Base):     # Terminal URL equals value
    assertion_type : Enum__Assertion__Type = Enum__Assertion__Type.URL_EQUALS
    expected       : Safe_Str__Url                                                  # The exact terminal URL expected
