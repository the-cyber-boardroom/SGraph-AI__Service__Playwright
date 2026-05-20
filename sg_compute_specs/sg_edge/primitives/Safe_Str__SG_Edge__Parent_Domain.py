# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Safe_Str__SG_Edge__Parent_Domain
# The parent domain that defines one edge (one isolation boundary), e.g.
# "cv.sgraph.ai". Slugs live under it (alice.cv.sgraph.ai); the proxy fleet is
# published at proxies.<parent> and the teardown counter at _state.<parent>.
# Lowercase DNS name: letters, digits, hyphens, dots; alnum ends. Max 253.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__SG_Edge__Parent_Domain(Safe_Str):
    regex             = re.compile(r'^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$')         # DNS name: lower-alnum, dots, hyphens; alnum ends
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 253
    allow_empty       = True
    to_lower_case     = True
    trim_whitespace   = True
