# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Topology__Render
# Screen 2 (Topology) content — the layered flow browser → wildcard → proxy fleet →
# slugs, the `check` diagram made interactive. PURE (no textual) → testable on 3.11.
# The selected slug (driven by ↑/↓ in the screen) gets a ▸ marker + bold; a Selected
# line previews what S4 will deep-dive. Idiom #3 (Topology / Wiring Map).
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State              import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot            import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Glyphs              import slug_glyph, yes_no

LIVE = Enum__SG_Edge__TUI__Slug_State.LIVE


def topology_markup(snapshot : Schema__SG_Edge__TUI__Snapshot, selected_index : int = -1) -> str:
    stamp = datetime.datetime.fromtimestamp(int(snapshot.captured_at), datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    lines = []
    lines.append(f'[bold]SG/Edge Topology[/]   target=[cyan]{snapshot.target}[/]  parent=[cyan]{snapshot.parent}[/]')
    lines.append(f'[dim]{stamp}[/]')
    lines.append('')

    if not snapshot.zone_exists:
        lines.append('[yellow]edge not provisioned[/] — no hosted zone for this parent')
        return '\n'.join(lines)

    wg, ws = yes_no(snapshot.wildcard)
    fg, fs = yes_no(len(snapshot.fleet_ips) > 0)
    lines.append('  Browser')
    lines.append(f'  [dim]http://<slug>.{snapshot.parent}[/]')
    lines.append('     │')
    lines.append('     ▼')
    lines.append(f'  [{ws}]{wg}[/] CloudFront / Wildcard   [dim]*.{snapshot.parent}[/]')
    lines.append('     │')
    lines.append('     ▼')
    lines.append(f'  [{fs}]{fg}[/] Edge Proxy fleet   [dim]({len(snapshot.fleet_ips)} IP)[/]')
    for ip in snapshot.fleet_ips:
        lines.append(f'       • {ip}')
    lines.append('     │')
    lines.append('     ▼')
    lines.append(f'  [bold]Vault backends (slugs)[/]   ({len(snapshot.slugs)})')
    if not snapshot.slugs:
        lines.append('       [dim](none registered)[/]')
    for index, slug in enumerate(snapshot.slugs):
        glyph, style = slug_glyph(slug.state)
        backend      = f' → {slug.backend_ip}:{slug.backend_port}' if slug.state == LIVE else ''
        label        = slug.slug[:16].ljust(16)
        if index == selected_index:
            lines.append(f'   ▸ [{style}]{glyph}[/] [bold]{label}[/] [dim]{slug.state}[/]{backend}')
        else:
            lines.append(f'     [{style}]{glyph}[/] {label} [dim]{slug.state}[/]{backend}')

    if 0 <= selected_index < len(snapshot.slugs):
        sel     = snapshot.slugs[selected_index]
        backend = f'{sel.backend_ip}:{sel.backend_port}' if sel.state == LIVE else '—'
        lines.append('')
        lines.append(f'  [bold]Selected:[/] {sel.slug}   [dim]{sel.fqdn}  state={sel.state}  backend={backend}[/]')
    return '\n'.join(lines)
