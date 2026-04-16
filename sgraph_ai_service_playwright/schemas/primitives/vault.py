# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Vault Key and Path Primitives
#
# Vault keys come in two formats:
#   Friendly:  "drum-hunt-6610"                         (lowercase + digits + hyphens)
#   Opaque:    "j4pyy0lhny8jx7osqn4lclhq:mzrp0li8"      (lowercase + digits + colons)
# Both must be accepted by Safe_Str__Vault_Key.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode

# @dev can you refactor each of these classes into its own file
#      you can put them in a folder with the same name as the current file
#      in this case /schemas/primitives/vault/Safe_Str__Vault_Key.py
class Safe_Str__Vault_Key(Safe_Str):                                                # Vault identifier — friendly or opaque
    max_length      = 128                                                           # Accommodate opaque keys with colon
    regex           = re.compile(r'[^a-z0-9\-:]')                                   # Lowercase + digits + hyphens + colons
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True                                                          # Default-constructible for Type_Safe fields
    trim_whitespace = True


class Safe_Str__Vault_Path(Safe_Str):                                               # Path within a vault
    max_length      = 1024                                                          # e.g. /sessions/openrouter/cookies.json
    regex           = re.compile(r'[^a-zA-Z0-9_\-./]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True                                                          # Default-constructible for Type_Safe fields
    trim_whitespace = True
