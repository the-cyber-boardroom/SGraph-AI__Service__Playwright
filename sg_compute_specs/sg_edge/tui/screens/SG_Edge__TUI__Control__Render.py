# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Control__Render
# Pure render for the Control Center panels (no textual) → testable on 3.11. Three
# builders: the STATE read (infra + checks; slugs are a DataTable, not markup), the
# ACTIONS surface (rendered greyed when the source can't act — capability-gating made
# visible, separation-guide rule 5), and the PREVIEW of what the next action will do
# (the simulate principle, rule 6 — a pure prediction from the snapshot, no mutation).
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State              import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Glyphs              import severity_glyph, yes_no

LIVE    = Enum__SG_Edge__TUI__Slug_State.LIVE
DORMANT = Enum__SG_Edge__TUI__Slug_State.DORMANT


def control_state_markup(snapshot) -> str:
    lines = ['[bold]STATE[/]']
    if not snapshot.zone_exists:
        lines.append('  [yellow]not provisioned[/] — press [bold]S[/] to set up the edge')
    else:
        dg, ds = yes_no(snapshot.deployed)
        wg, ws = yes_no(snapshot.wildcard)
        fg, fs = yes_no(len(snapshot.fleet_ips) > 0)
        lines.append(f'  [{ds}]{dg}[/] deployed   [{ws}]{wg}[/] wildcard   [{fs}]{fg}[/] fleet: {len(snapshot.fleet_ips)}')
        lines.append(f'  [dim]zero_streak: {snapshot.zero_streak}/3   slugs: {len(snapshot.slugs)}[/]')
    if snapshot.issues:
        lines.append('')
        lines.append('[bold]Checks[/]')
        for issue in snapshot.issues:
            glyph, style = severity_glyph(issue.severity)
            lines.append(f'  [{style}]{glyph}[/] [dim]{issue.area}[/]  {issue.message}')
    return '\n'.join(lines)


def control_actions_markup(can_act : bool, reason : str = '') -> str:
    lines = ['[bold]ACTIONS[/]']
    if not can_act:
        lines.append(f'  [yellow]disabled[/] — {reason or "not available on this target"}')
        dim = lambda text: f'  [dim]{text}[/]'
        lines += [dim('n register      N register dormant'),
                  dim('u unregister    g request'),
                  dim('S setup         X teardown')]
        return '\n'.join(lines)
    lines += ['  [cyan]n[/] register       [cyan]N[/] register dormant',
              '  [cyan]u[/] unregister     [cyan]g[/] request',
              '  [cyan]S[/] setup          [cyan]X[/] teardown']
    return '\n'.join(lines)


def request_prediction(snapshot, slug : str) -> str:                                 # pure: what `request <slug>` would return, from the snapshot
    match = next((s for s in snapshot.slugs if s.slug == slug), None)
    if match is None:
        return '404 not recognised'
    if match.state == LIVE:
        return f'200 welcome → {match.backend_ip}:{match.backend_port}'
    if match.state == DORMANT:
        return '503 dormant (Vault Waker would wake it)'
    return 'orphan backend (TXT without A)'


def control_preview_markup(snapshot, slug : str) -> str:
    lines = ['[bold]PREVIEW[/]']
    if not slug:
        lines.append('  [dim](type a slug or select a row)[/]')
        return '\n'.join(lines)
    registered = any(s.slug == slug for s in snapshot.slugs)
    lines.append(f'  [cyan]g[/] request [bold]{slug}[/] → {request_prediction(snapshot, slug)}')
    if registered:
        lines.append(f'  [cyan]u[/] unregister [bold]{slug}[/] → removes A + TXT')
    else:
        lines.append(f'  [cyan]n[/] register [bold]{slug}[/] → writes A + _sg.{slug} TXT')
    return '\n'.join(lines)
