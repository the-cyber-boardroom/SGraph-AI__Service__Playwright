# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__Bot__Category
# Derived field — Bot__Classifier maps cs_user_agent to one of these categories.
# Drives the "Bot vs human ratio over time" panel.
#   HUMAN        — UA matches no bot signature
#   BOT_KNOWN    — UA matches a named-bot pattern (Googlebot, Bingbot, etc.)
#   BOT_GENERIC  — UA contains "bot" / "spider" / "crawler" but no known name
#   UNKNOWN      — UA is empty or unparseable
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__Bot__Category(str, Enum):
    HUMAN       = 'human'
    BOT_KNOWN   = 'bot_known'
    BOT_GENERIC = 'bot_generic'
    UNKNOWN     = 'unknown'

    def __str__(self):
        return self.value
