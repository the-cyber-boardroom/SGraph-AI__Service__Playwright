# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui: Tui__Text
# Shared pure render helpers reused by every TUI render module (cf-logs, s3 browser,
# and future sg aws screens). No textual, no rich — testable on 3.11. Keeping these in
# one place is the "component-first" rule applied to render primitives: escape once,
# size once, stamp once.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime


def esc(text : str) -> str:                                                          # neutralise Rich markup so file content can't open a tag
    return str(text).replace('[', r'\[')


def human_size(n : int) -> str:
    n = int(n)
    if n < 1024:                 return f'{n}B'
    if n < 1024 * 1024:          return f'{n / 1024:.1f}KB'
    if n < 1024 * 1024 * 1024:   return f'{n / (1024 * 1024):.1f}MB'
    return f'{n / (1024 * 1024 * 1024):.1f}GB'


def human_count(n : int) -> str:
    n = int(n)
    if n < 1000:        return str(n)
    if n < 1_000_000:   return f'{n / 1000:.1f}k'
    return f'{n / 1_000_000:.1f}M'


def ts_utc(epoch : float, fmt : str = '%Y-%m-%d %H:%M:%S UTC') -> str:
    return datetime.datetime.fromtimestamp(float(epoch), datetime.timezone.utc).strftime(fmt)


def hhmmss(epoch : float) -> str:
    return datetime.datetime.fromtimestamp(float(epoch), datetime.timezone.utc).strftime('%H:%M:%S')
