# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Docker__Render
# "Local Docker" content — what containers are running on the operator's machine.
# PURE (no textual) → testable on 3.11. `docker_lines()` is reused both by the
# standalone Docker screen and by the Deployment screen's LOCAL DOCKER section.
# Honest: an unreachable daemon renders a clear note, not fabricated rows.
# ═══════════════════════════════════════════════════════════════════════════════

STATE_GLYPH = {'running': ('●', 'green'),
               'exited' : ('✗', 'red'),
               'created': ('◐', 'yellow'),
               'paused' : ('◐', 'yellow'),
               'restarting': ('◐', 'yellow')}


def _glyph(state : str) -> tuple:
    return STATE_GLYPH.get(str(state).strip().lower(), ('·', 'white'))


def _wrap(text, style, styled):
    return f'[{style}]{text}[/]' if styled else text


def docker_lines(pod_list, available : bool, styled : bool = True) -> list:
    pods  = list(pod_list.pods)
    lines = []
    if not available:
        lines.append(_wrap('docker daemon not reachable', 'yellow', styled) + ' — is it running? (try: sg edge tui diagnose)')
        return lines
    if not pods:
        lines.append('  (no containers running)' if not styled else '  [dim](no containers running)[/]')
        return lines
    for pod in sorted(pods, key=lambda p: str(p.name)):
        glyph, style = _glyph(pod.state)
        name         = str(pod.name)[:24].ljust(24)
        image        = str(pod.image)[:30].ljust(30)
        status       = str(pod.status)
        lines.append(f'  {_wrap(glyph, style, styled)} {name} {image} {status}')
    return lines


def docker_markup(pod_list, available : bool) -> str:
    return _render(pod_list, available, styled=True)


def docker_plain(pod_list, available : bool) -> str:
    return _render(pod_list, available, styled=False)


def _render(pod_list, available : bool, styled : bool) -> str:
    count = len(pod_list.pods)
    head  = f'Local Docker   ({count} container{"s" if count != 1 else ""})'
    lines = [f'[bold]SG/Edge — {head}[/]' if styled else f'SG/Edge — {head}']
    lines.append(('[dim]running containers on this host (docker ps)[/]' if styled
                  else 'running containers on this host (docker ps)'))
    lines.append('')
    lines += docker_lines(pod_list, available, styled)
    return '\n'.join(lines)
