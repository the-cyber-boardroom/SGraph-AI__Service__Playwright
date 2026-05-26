# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Assertion__Http_Header_Present
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Header__Name           import Safe_Str__Http__Header__Name
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url__Path                      import Safe_Str__Url__Path

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.assertions.Schema__Journey__Assertion__Base               import Schema__Journey__Assertion__Base


class Schema__Journey__Assertion__Http_Header_Present(Schema__Journey__Assertion__Base):  # A captured flow carries a header
    assertion_type : Enum__Assertion__Type = Enum__Assertion__Type.HTTP_HEADER_PRESENT
    header_name    : Safe_Str__Http__Header__Name                                    # Response header expected present (case-insensitive)
    url_substring  : Safe_Str__Url__Path = None                                     # Which flow (request URL-path contains); None = first/any
