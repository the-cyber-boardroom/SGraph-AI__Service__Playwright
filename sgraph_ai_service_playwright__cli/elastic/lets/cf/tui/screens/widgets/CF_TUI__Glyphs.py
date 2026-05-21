# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Glyphs
# Status glyph/colour + sparkline + proportion-bar helpers for the CF-logs screens.
# Shared so the same state means the same thing everywhere (colour is semantic, not
# decorative). Pure — no textual, no rich import — returns plain strings / (text,
# style) pairs the view layer embeds as Rich markup. Runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

SPARK_CHARS = '▁▂▃▄▅▆▇█'
BAR_FULL    = '▓'
BAR_EMPTY   = '░'

STATUS_STYLE = {'1xx': 'dim', '2xx': 'green', '3xx': 'cyan',
                '4xx': 'yellow', '5xx': 'red', 'other': 'magenta'}


def status_style(label : str) -> str:
    return STATUS_STYLE.get(label, 'white')


def sparkline(values : list) -> str:                                                 # [1,4,2,8] → "▁▄▂█"; flat/empty series degrade cleanly
    nums = [int(v) for v in values]
    if not nums:
        return ''
    hi = max(nums)
    lo = min(nums)
    if hi == lo:
        return SPARK_CHARS[0] * len(nums) if hi == 0 else SPARK_CHARS[-1] * len(nums)
    span = hi - lo
    out  = []
    for n in nums:
        idx = int((n - lo) / span * (len(SPARK_CHARS) - 1))
        out.append(SPARK_CHARS[idx])
    return ''.join(out)


def bar(fraction : float, width : int = 10) -> str:                                  # 0.61, 10 → "▓▓▓▓▓▓░░░░"
    fraction = max(0.0, min(1.0, fraction))
    filled   = int(round(fraction * width))
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


def pct(part : int, whole : int) -> int:                                            # integer percent, 0 when whole is 0 (never divide-by-zero)
    if not whole:
        return 0
    return int(round(part * 100 / whole))
