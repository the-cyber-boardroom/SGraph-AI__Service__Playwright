# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Billing__Window__Resolver
# Resolves a CLI keyword verb ('last-48h', 'week', 'mtd') to a
# (start, end, granularity) tuple of YYYY-MM-DD strings suitable for passing
# directly to Cost Explorer. The 'window' verb is handled in Cli__Billing
# directly (start/end passed as arguments) and does not go through here.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Billing__Window__Resolver(Type_Safe):

    def resolve(self, keyword: str) -> tuple:                                         # Maps a keyword verb to (start_str, end_str, granularity_str)
        today = datetime.date.today()
        if keyword == 'last-48h':                                                     # Cost Explorer DAILY: start = today-2, end = today (exclusive)
            return str(today - datetime.timedelta(days=2)), str(today), 'DAILY'
        if keyword == 'week':
            return str(today - datetime.timedelta(days=7)), str(today), 'DAILY'
        if keyword == 'mtd':
            return str(today.replace(day=1)), str(today), 'DAILY'
        raise ValueError(f'Unknown window keyword: {keyword!r}')                     # 'window' is handled by the caller; any other string is a bug
