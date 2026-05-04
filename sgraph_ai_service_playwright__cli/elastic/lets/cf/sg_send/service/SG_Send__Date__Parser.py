# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — SG_Send__Date__Parser
# Parses the user-friendly date strings the `sg-send` commands accept.
# Per the user's call: "we can assume this is 2026" — so a 2-segment input
# is interpreted as MM/DD with year 2026.  Wider forms allow explicit year.
#
# Accepted formats (slashes or hyphens, both work):
#   04/25         → year=2026, month=4,  day=25
#   04/25/14      → year=2026, month=4,  day=25, hour=14
#   2026/04/25    → year=2026, month=4,  day=25
#   2026/04/25/14 → year=2026, month=4,  day=25, hour=14
#   2026-04-25    → same shape
#
# Returns a tuple (year, month, day, hour_or_none).  Raises ValueError on
# malformed input — caller surfaces as a friendly CLI error.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional, Tuple


DEFAULT_YEAR = 2026                                                                 # Hardcoded per the user — refactor when sg-send goes multi-year


def parse_sg_send_date(spec: str) -> Tuple[int, int, int, Optional[int]]:           # (year, month, day, hour_or_none)
    if not spec or not isinstance(spec, str):
        raise ValueError(f'date is required; got {spec!r}')

    # Normalise separators
    parts = spec.replace('-', '/').strip('/').split('/')

    if len(parts) == 2:                                                              # MM/DD — assume 2026
        month, day = parts
        year       = DEFAULT_YEAR
        hour       = None
    elif len(parts) == 3:
        # Could be MM/DD/HH or YYYY/MM/DD — disambiguate by length of first part
        if len(parts[0]) == 4:                                                       # YYYY/MM/DD
            year, month, day = parts
            hour = None
        else:                                                                        # MM/DD/HH
            month, day, hour = parts
            year             = DEFAULT_YEAR
    elif len(parts) == 4:                                                            # YYYY/MM/DD/HH
        year, month, day, hour = parts
    else:
        raise ValueError(f'expected MM/DD, MM/DD/HH, YYYY/MM/DD, or YYYY/MM/DD/HH; got {spec!r}')

    try:
        y = int(year)
        m = int(month)
        d = int(day)
        h = int(hour) if hour is not None else None
    except (ValueError, TypeError):
        raise ValueError(f'date components must be integers; got {spec!r}')

    if y < 2020 or y > 2100:                                                         # Sanity bounds
        raise ValueError(f'year {y} out of range (2020-2100)')
    if m < 1 or m > 12:
        raise ValueError(f'month {m} out of range (1-12)')
    if d < 1 or d > 31:
        raise ValueError(f'day {d} out of range (1-31)')
    if h is not None and (h < 0 or h > 23):
        raise ValueError(f'hour {h} out of range (0-23)')

    return y, m, d, h


def s3_prefix_for_date(year: int, month: int, day: int, hour: Optional[int] = None) -> str:    # → "cloudfront-realtime/2026/04/25/" or "cloudfront-realtime/2026/04/25/14"
    base = f'cloudfront-realtime/{year:04d}/{month:02d}/{day:02d}'
    if hour is not None:
        return f'{base}/{hour:02d}'
    return base + '/'


def render_date_label(year: int, month: int, day: int, hour: Optional[int] = None) -> str:    # Human-readable label for table headers etc.
    if hour is not None:
        return f'{year:04d}-{month:02d}-{day:02d} hour {hour:02d}:00'
    return f'{year:04d}-{month:02d}-{day:02d}'
