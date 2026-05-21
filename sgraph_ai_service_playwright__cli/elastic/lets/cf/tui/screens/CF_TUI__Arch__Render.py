# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Arch__Render
# Deployed-architecture wiring as Rich-markup (and a plain variant). PURE — no
# textual, no rich import — testable on 3.11. Draws the real flow Internet →
# CloudFront → (Firehose, UNVERIFIED) → S3 → LETS → consumers, plus the CloudWatch
# log groups. Unconfirmed wiring is marked ⚠ UNVERIFIED; failed reads are shown as
# honest error lines — nothing is fabricated.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Arch_Snapshot import Schema__CF_TUI__Arch_Snapshot


def _esc(text : str) -> str:
    return text.replace('[', r'\[')


def arch_markup(snapshot : Schema__CF_TUI__Arch_Snapshot) -> str:
    lines = []
    stamp = datetime.datetime.fromtimestamp(int(snapshot.captured_at), datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    lines.append('[bold]CF Deployed Architecture[/]')
    lines.append(f'[dim]{stamp}  ·  who is wired to what (live via sg aws)[/]')
    lines.append('')
    lines.append('  [dim]Internet[/]')
    lines.append('     [dim]│[/]')
    lines.append('     [dim]▼[/]')

    lines.append(f'  [bold]CloudFront[/]  ({len(snapshot.distributions)} distribution(s))')
    if snapshot.cf_error:
        lines.append(f'     [red]✗ {_esc(snapshot.cf_error)}[/]')
    elif not snapshot.distributions:
        lines.append('     [dim](none)[/]')
    for d in snapshot.distributions:
        glyph = '[green]●[/]' if d.enabled else '[dim]○[/]'
        alias = f'  [dim]{_esc(d.aliases)}[/]' if d.aliases else ''
        lines.append(f'     {glyph} [cyan]{d.distribution_id[:16].ljust(16)}[/] {_esc(d.domain)[:30].ljust(30)} [dim]{d.status}[/]{alias}')
        lines.append(f'        [yellow]⚠ rt-log → Firehose: {d.rt_log_status}[/]')

    lines.append('     [dim]│  real-time logs[/]')
    lines.append('     [dim]▼[/]')
    lines.append('  [bold]Firehose[/]  [yellow]⚠ UNVERIFIED[/]')
    lines.append(f'     [dim]{_esc(snapshot.firehose_note)}[/]')
    lines.append('     [dim]│[/]')
    lines.append('     [dim]▼[/]')

    reach = '[green]✓ reachable[/]' if snapshot.bucket_reachable else '[red]✗ unreachable[/]'
    lines.append(f'  [bold]S3[/]  {reach}')
    lines.append(f'     [cyan]{_esc(snapshot.bucket_name)}[/]')
    if snapshot.s3_error:
        lines.append(f'     [red]✗ {_esc(snapshot.s3_error)}[/]')
    else:
        lines.append(f'     [dim]cloudfront-realtime/  ({snapshot.bucket_top_folders} top-level partition(s))[/]')
    lines.append('     [dim]│[/]')
    lines.append('     [dim]▼[/]')
    lines.append('  [bold]LETS stages[/] → consumers  [dim](Kibana · this TUI)[/]')
    lines.append('')

    lines.append(f'  [bold]CloudWatch Log Groups[/]  ({len(snapshot.log_groups)})')
    if snapshot.logs_error:
        lines.append(f'     [red]✗ {_esc(snapshot.logs_error)}[/]')
    elif not snapshot.log_groups:
        lines.append('     [dim](none)[/]')
    for g in snapshot.log_groups[:12]:
        ret = f'{g.retention_days}d' if g.retention_days else 'never'
        lines.append(f'     [dim]·[/] {_esc(g.name)[:48].ljust(48)} [dim]retain {ret}[/]')

    return '\n'.join(lines)


def arch_plain(snapshot : Schema__CF_TUI__Arch_Snapshot) -> str:
    out = ['CF Deployed Architecture', 'Internet -> CloudFront -> Firehose(UNVERIFIED) -> S3 -> LETS -> consumers', '']
    out.append(f'CloudFront ({len(snapshot.distributions)})' + (f'  ERROR: {snapshot.cf_error}' if snapshot.cf_error else ''))
    for d in snapshot.distributions:
        out.append(f'  {d.distribution_id}  {d.domain}  {d.status}  rt-log:{d.rt_log_status}')
    out.append(f'Firehose: UNVERIFIED — {snapshot.firehose_note}')
    out.append(f'S3: {snapshot.bucket_name}  reachable={snapshot.bucket_reachable}' + (f'  ERROR: {snapshot.s3_error}' if snapshot.s3_error else ''))
    out.append(f'CloudWatch Log Groups ({len(snapshot.log_groups)})' + (f'  ERROR: {snapshot.logs_error}' if snapshot.logs_error else ''))
    for g in snapshot.log_groups[:12]:
        out.append(f'  {g.name}')
    return '\n'.join(out)
