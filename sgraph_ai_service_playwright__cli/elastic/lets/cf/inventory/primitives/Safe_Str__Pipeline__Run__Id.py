# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Pipeline__Run__Id
# Identifier for a single LETS pipeline run. The service generates ids of the
# form "{utc-iso8601}-{source}-{verb}-{shortsha}", e.g.
#   "20260425T103042Z-cf-realtime-load-a3f2"
# but the primitive itself only enforces a generic ASCII-id shape so callers
# can pass simpler test fixtures (e.g. "test-run-1") without fighting the
# regex. The service-layer generator is the source of truth for the format.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Pipeline__Run__Id(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9_\-]{1,128}$')                       # Generic ASCII-id shape; precise format enforced by the service-side generator
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 128
    allow_empty       = True                                                        # Empty → service auto-generates
    trim_whitespace   = True
