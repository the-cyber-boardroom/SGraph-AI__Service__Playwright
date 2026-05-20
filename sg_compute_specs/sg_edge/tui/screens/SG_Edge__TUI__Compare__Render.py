# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Compare__Render
# Screen 3 (Local vs Edge) content. PURE — no textual import — so it is unit-testable
# on 3.11; the Textual screen drops the markup into a Static, and the CLI no-TTY path
# uses the plain variant. Honest TWO-way only (local vs edge): no "Deployed" column,
# no cross-service version matrix (out of scope for sg_edge). Diff via the T1
# Comparison service; a per-row sync glyph + a drift summary line.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Sync_State              import Enum__SG_Edge__TUI__Sync_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot            import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Comparison                  import SG_Edge__TUI__Comparison
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Glyphs              import sync_glyph

IN_SYNC    = Enum__SG_Edge__TUI__Sync_State.IN_SYNC
LOCAL_ONLY = Enum__SG_Edge__TUI__Sync_State.LOCAL_ONLY
EDGE_ONLY  = Enum__SG_Edge__TUI__Sync_State.EDGE_ONLY


def compare_markup(local : Schema__SG_Edge__TUI__Snapshot, aws : Schema__SG_Edge__TUI__Snapshot) -> str:
    return _render(local, aws, styled=True)


def compare_plain(local : Schema__SG_Edge__TUI__Snapshot, aws : Schema__SG_Edge__TUI__Snapshot) -> str:
    return _render(local, aws, styled=False)


def _render(local, aws, styled : bool) -> str:
    rows  = SG_Edge__TUI__Comparison().compare(local, aws)
    stamp = datetime.datetime.fromtimestamp(int(local.captured_at), datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    lines = []
    lines.append(_b('SG/Edge — Local vs Edge', styled))
    lines.append(_dim(f'local: {local.parent} ({_zone_word(local)})   edge: {aws.parent} ({_zone_word(aws)})', styled))
    lines.append(_dim(stamp, styled))
    lines.append('')
    lines.append(_b(f'{"COMPONENT":<22} {"LOCAL":<7} {"EDGE":<7}', styled))

    for row in rows:
        glyph, style = sync_glyph(row.sync_state)
        mark         = _wrap(glyph, style, styled)
        local_cell   = _present(row.local_present, styled)
        edge_cell    = _present(row.edge_present,  styled)
        label        = str(row.sync_state).replace('_', ' ')
        lines.append(f'  {mark} {row.name[:20]:<20} {local_cell:<7} {edge_cell:<7} {_dim(label, styled)}')

    drift = [r for r in rows if r.sync_state != IN_SYNC]
    local_only = sum(1 for r in drift if r.sync_state == LOCAL_ONLY)
    edge_only  = sum(1 for r in drift if r.sync_state == EDGE_ONLY)
    lines.append('')
    if drift:
        lines.append(_wrap('⚠', 'yellow', styled) +
                     f' DRIFT: {len(drift)} difference(s) — {local_only} local-only, {edge_only} edge-only  '
                     f'[{len(rows) - len(drift)} in sync]')
    else:
        lines.append(_wrap('●', 'green', styled) + f' IN SYNC: all {len(rows)} component(s) match')
    return '\n'.join(lines)


def _present(flag : bool, styled : bool) -> str:                                     # ✓ / ✗ cell (kept un-styled — colour lives on the sync glyph)
    return '✓' if flag else '✗'


def _zone_word(snapshot) -> str:
    return 'provisioned' if snapshot.zone_exists else 'not provisioned'


def _wrap(text : str, style : str, styled : bool) -> str:
    return f'[{style}]{text}[/]' if styled else text


def _b(text : str, styled : bool) -> str:
    return f'[bold]{text}[/]' if styled else text


def _dim(text : str, styled : bool) -> str:
    return f'[dim]{text}[/]' if styled else text
