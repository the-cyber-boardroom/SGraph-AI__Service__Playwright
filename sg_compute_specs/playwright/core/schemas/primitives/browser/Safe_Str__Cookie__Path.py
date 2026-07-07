# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Cookie__Path primitive (set_cookie verb)
#
# Cookie Path attribute: an absolute URL path ("/", "/app", ...). Character class
# mirrors Safe_Str__Url__Permissive's RFC 3986 path set (pchar + "/"); must start
# with "/". Strict full-match.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


COOKIE_PATH_REGEX = re.compile(r"^/[a-zA-Z0-9\-._~%!$&'()*+,;=:@/]*$")              # "/" + RFC 3986 pchar set


class Safe_Str__Cookie__Path(Safe_Str):                                             # Cookie Path attribute (absolute URL path)
    max_length        = 1024
    regex             = COOKIE_PATH_REGEX
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True                                                        # Default-constructible; Credentials__Loader defaults to '/' when domain-form is used
    trim_whitespace   = True
