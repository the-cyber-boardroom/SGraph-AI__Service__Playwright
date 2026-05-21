# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Events__Render
# Screen 5 (Live Event Stream) content. PURE (no textual) → testable on 3.11.
# The feed is honest: events are the T1 Differ's observed state transitions (NOT a
# per-request stream — that needs the observability source, a later swap). Sparklines
# are honest too — counts the TUI measured itself (total / live slugs, fleet size),
# never rps/cost. Supports a kind filter and a paused indicator.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Event_Kind              import Enum__SG_Edge__TUI__Event_Kind
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Glyphs              import event_glyph

EK = Enum__SG_Edge__TUI__Event_Kind

FILTER_KINDS = {'slugs' : {EK.SLUG_REGISTERED, EK.WENT_LIVE, EK.WENT_DORMANT, EK.REMOVED},
                'fleet' : {EK.FLEET_CHANGED},
                'issues': {EK.ISSUE, EK.CLEARED}}

SPARK_BARS  = '▁▂▃▄▅▆▇█'
FEED_LIMIT  = 14                                                                     # visible feed rows


def sparkline(values : list) -> str:
    if not values:
        return ''
    lo, hi = min(values), max(values)
    if hi == lo:
        return SPARK_BARS[0] * len(values)
    span = hi - lo
    return ''.join(SPARK_BARS[int((v - lo) / span * (len(SPARK_BARS) - 1))] for v in values)


def events_markup(snapshot, events : list, metrics, active_filter : str = 'all', paused : bool = False) -> str:
    kinds = FILTER_KINDS.get(active_filter)
    shown = [e for e in events if (kinds is None or e.kind in kinds)]

    lines = []
    pause_tag = ' [yellow]⏸ PAUSED[/]' if paused else ''                              # not "[PAUSED]" — literal [..] collides with Rich markup
    lines.append(f'[bold]SG/Edge Live Activity[/]   target=[cyan]{snapshot.target}[/]  parent=[cyan]{snapshot.parent}[/]{pause_tag}')
    lines.append(f'[dim]events are observed state transitions (no per-request stream — pending observability)[/]')
    lines.append('')

    lines.append(f'[bold]EVENTS[/]  [dim](newest first — {len(shown)} shown, filter: {active_filter})[/]')
    if not shown:
        lines.append('  [dim](no events yet — change state in another pane and watch)[/]')
    for event in shown[:FEED_LIMIT]:
        glyph, style = event_glyph(event.kind)
        stamp        = datetime.datetime.fromtimestamp(int(event.ts), datetime.timezone.utc).strftime('%H:%M:%S')
        lines.append(f'  [dim]{stamp}[/]  [{style}]{glyph}[/] {event.detail}')
    lines.append('')

    lines.append('[bold]THROUGHPUT[/]  [dim](counts the TUI measured — not rps)[/]')
    lines.append(f'  total slugs  {sparkline(metrics.values(metrics.total_slugs))}')
    lines.append(f'  live slugs   {sparkline(metrics.values(metrics.live_slugs))}')
    lines.append(f'  fleet size   {sparkline(metrics.values(metrics.fleet_size))}')
    lines.append('')
    lines.append('[dim]FILTER: (a)ll  (s)lugs  (f)leet  (i)ssues     (space) pause  (c)lear[/]')
    return '\n'.join(lines)
