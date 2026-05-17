# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Creds__TTL__Parser
# Parses human-readable TTL strings ('1h', '30m', '2h') to seconds.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Creds__TTL__Parser(Type_Safe):

    _PATTERN = re.compile(r'^(\d+)(h|m|s)$')

    _MULTIPLIERS = {'h': 3600, 'm': 60, 's': 1}

    def parse(self, ttl: str) -> int:                                           # Returns seconds; raises ValueError on bad format
        ttl = ttl.strip()
        m   = self._PATTERN.match(ttl)
        if not m:
            raise ValueError(f"Invalid TTL format '{ttl}' — expected e.g. '1h', '30m', '120s'")
        amount, unit = int(m.group(1)), m.group(2)
        return amount * self._MULTIPLIERS[unit]
