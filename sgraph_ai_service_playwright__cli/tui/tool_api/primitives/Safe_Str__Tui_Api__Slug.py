# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Safe_Str__Tui_Api__Slug
# A dotted, lowercase API/tool slug, e.g. 'sg-aws.s3' or 'sg-edge.slugs'.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Tui_Api__Slug(Safe_Str):
    regex       = re.compile(r'[^a-z0-9._-]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    max_length  = 128
    allow_empty = True
