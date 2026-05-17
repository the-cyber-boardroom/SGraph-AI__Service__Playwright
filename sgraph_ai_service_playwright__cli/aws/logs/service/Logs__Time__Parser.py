# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Logs__Time__Parser
# Converts human-friendly time expressions to epoch milliseconds.
# Accepts:
#   Relative : "30s", "5m", "2h", "1d", "7d"
#   Absolute : ISO 8601 UTC  "2026-05-17T14:00:00Z"
# ═══════════════════════════════════════════════════════════════════════════════

import re
import time

from datetime                        import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe


_RELATIVE = re.compile(r'^(\d+)(s|m|h|d)$')

_UNIT_SECONDS = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}


class Logs__Time__Parser(Type_Safe):

    def now_ms(self) -> int:                                                        # current epoch ms
        return int(time.time() * 1000)

    def parse(self, expr: str) -> int:                                              # expr → epoch ms; raises ValueError on bad input
        expr = expr.strip()
        m = _RELATIVE.match(expr)
        if m:
            amount = int(m.group(1))
            unit   = m.group(2)
            return self.now_ms() - amount * _UNIT_SECONDS[unit] * 1000
        try:                                                                        # try ISO 8601 UTC
            if not expr.endswith('Z'):
                raise ValueError(f'Absolute time must be UTC (end with Z): {expr!r}')
            dt = datetime.fromisoformat(expr[:-1])
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            raise ValueError(
                f'Cannot parse time expression {expr!r}. '
                f'Use e.g. "30s", "5m", "2h", "1d" or ISO UTC "2026-05-17T14:00:00Z".'
            )

    def parse_optional(self, expr: str | None, default_offset_ms: int = 3600 * 1000) -> int:
        if not expr:
            return self.now_ms() - default_offset_ms                               # default: 1 hour ago
        return self.parse(expr)
