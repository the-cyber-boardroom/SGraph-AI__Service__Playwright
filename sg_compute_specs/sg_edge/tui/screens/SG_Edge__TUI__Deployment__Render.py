# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Deployment__Render
# Screen 1 (Deployment Reality) content as a Rich-markup string. PURE — no textual,
# no rich import — so the content is unit-testable on 3.11; the Textual screen just
# drops this into a Static. Sections answer "what is deployed right now": edge
# infrastructure, proxy fleet, slugs, checks. Panes with no real data (instance ids,
# vault servers) are labelled "pending Slice 5" — never fabricated.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State              import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot            import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Glyphs              import slug_glyph, severity_glyph, yes_no
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Docker__Render              import docker_lines

LIVE = Enum__SG_Edge__TUI__Slug_State.LIVE


def deployment_markup(snapshot : Schema__SG_Edge__TUI__Snapshot, containers=None, docker_available : bool = True) -> str:
    lines = []
    stamp = datetime.datetime.fromtimestamp(int(snapshot.captured_at), datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    lines.append(f'[bold]SG/Edge Deployment Reality[/]   target=[cyan]{snapshot.target}[/]  parent=[cyan]{snapshot.parent}[/]')
    lines.append(f'[dim]{stamp}[/]')
    lines.append('')

    if not snapshot.zone_exists:
        lines.append('[yellow]edge not provisioned[/] — no hosted zone for this parent')
    else:
        lines.append('[bold]EDGE INFRASTRUCTURE[/]')
        lines.append(_flag_row('Hosted zone', snapshot.parent, snapshot.zone_exists))
        lines.append(_flag_row('Wildcard',    f'*.{snapshot.parent}  (CloudFront equiv)', snapshot.wildcard))
        lines.append(f'  [dim]·[/] Teardown counter   zero_streak={snapshot.zero_streak}')
        lines.append('')

        lines.append('[bold]PROXY FLEET[/]')
        lines.append(_flag_row('Proxy fleet', f'proxies.{snapshot.parent}  ({len(snapshot.fleet_ips)} IP)', len(snapshot.fleet_ips) > 0))
        for ip in snapshot.fleet_ips:
            lines.append(f'      • {ip}')
        lines.append('  [dim]instance id / AZ / uptime: pending Slice 5[/]')
        lines.append('')

        lines.append('[bold]VAULT SERVERS[/]')
        lines.append('  [dim]pending Slice 5 — no EC2 launcher wired yet[/]')
        lines.append('')

        lines.append(f'[bold]REGISTERED SLUGS[/]  ({len(snapshot.slugs)})')
        if not snapshot.slugs:
            lines.append('  [dim](none)[/]')
        for slug in snapshot.slugs:
            glyph, style = slug_glyph(slug.state)
            backend      = f' → {slug.backend_ip}:{slug.backend_port}' if slug.state == LIVE else ''
            lines.append(f'  [{style}]{glyph}[/] {slug.slug[:18].ljust(18)} [dim]{slug.state}[/]{backend}')

    if containers is not None:
        lines.append('')
        lines.append(f'[bold]LOCAL DOCKER[/]  ({len(containers.pods)})')
        lines += docker_lines(containers, docker_available, styled=True)

    if snapshot.issues:
        lines.append('')
        lines.append('[bold]CHECKS[/]')
        for issue in snapshot.issues:
            glyph, style = severity_glyph(issue.severity)
            lines.append(f'  [{style}]{glyph}[/] [dim]{issue.area}[/]  {issue.message}')

    return '\n'.join(lines)


def _flag_row(label : str, detail : str, flag : bool) -> str:
    glyph, style = yes_no(flag)
    return f'  [{style}]{glyph}[/] {label.ljust(18)} {detail}'                        # pad short labels; never truncate
