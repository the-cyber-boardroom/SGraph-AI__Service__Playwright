# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Cookie__Same_Site (set_cookie verb)
#
# The capitalised VALUES ("Strict" / "Lax" / "None") are exactly what Playwright's
# context.add_cookies expects for the sameSite field — serialise via .value.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Cookie__Same_Site(str, Enum):                                           # SameSite attribute for the set_cookie step
    STRICT = "Strict"
    LAX    = "Lax"
    NONE   = "None"

    def __str__(self): return self.value
