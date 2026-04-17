# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Basic_Auth__Password
#
# Same rationale as Safe_Str__Basic_Auth__Username: proxy passwords in the wild
# carry hyphens, dots, and sometimes punctuation. osbot_utils' Safe_Str__Password
# enforces a min_length=8 that would reject short test tokens — we deliberately
# relax that here because the vault, not the schema, is where credential
# strength policy lives.
#
# Never logged / never inspected by other components — only the CDP
# Fetch.continueWithAuth payload consumes it.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str


class Safe_Str__Basic_Auth__Password(Safe_Str):
    regex      = re.compile(r'[^a-zA-Z0-9_\-.!@#$%^&*()]')                          # Mirrors Safe_Str__Password's char class, minus the min_length floor
    max_length = 256
