# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Browser Interaction Primitives
#
# Safe_Str__JS__Expression accepts any JS string up to 4 KB; the dispatcher
# validates against a configured allowlist and rejects on mismatch (the 04/09
# architect constraint). Security gating is NOT at the primitive level.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


ANY_CHARS_REGEX = re.compile(r'.*', re.DOTALL)                                      # Matches anything including newlines


class Safe_Str__Selector(Safe_Str):                                                 # CSS or XPath selector
    max_length        = 1024                                                        # Some frameworks emit long selectors
    regex             = ANY_CHARS_REGEX                                             # No content restriction — selectors use any chars
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True                                                        # MATCH mode needs strict_validation
    allow_empty       = False
    trim_whitespace   = True


class Safe_Str__Browser__Launch_Arg(Safe_Str):                                      # Single chromium launch arg
    max_length      = 256
    regex           = re.compile(r'[^a-zA-Z0-9_\-=./:,*?@]')                        # Reasonable flag character set
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = False


class Safe_Str__JS__Expression(Safe_Str):                                           # JS expression for page.evaluate()
    max_length        = 4096                                                        # Reasonable limit
    regex             = ANY_CHARS_REGEX                                             # Content validation at dispatcher level (allowlist)
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = False
