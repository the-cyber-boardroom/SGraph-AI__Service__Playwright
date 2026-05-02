# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Icon
# Single emoji or short Unicode label for the plugin UI card.
# Strips only C0/C1 control characters; all printable Unicode (incl. emoji) allowed.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Safe_Str__Icon(Safe_Str):
    regex      = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')   # strip control chars only
    max_length = 32
