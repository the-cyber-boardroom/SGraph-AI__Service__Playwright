# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Logs__Render
# Logs surface (use case 1): the records in the sink + a per-request trace. PURE —
# no textual/rich import; unit-testable on 3.11. Newest records last (sink order).
# ═══════════════════════════════════════════════════════════════════════════════


def _verdict_glyph(verdict: str):
    return ('⚠', 'red') if verdict == 'block' else ('●', 'green')


def logs_markup(records, sink_label: str, selected_index: int = 0) -> str:
    lines = ['[bold]SG/Sentinel — Logs[/]  [dim](use case 1: real-time visibility)[/]',
             f'[dim]sink: {sink_label}[/]', '']
    lines.append('  [dim]REQUEST                  RECEIVED              VERDICT  RULE  PATH[/]')
    for i, r in enumerate(records):
        glyph, style = _verdict_glyph(r.verdict.value)
        marker       = '[reverse]▸[/]' if i == selected_index else ' '
        path         = str(r.path) or '(empty)'
        lines.append(f'{marker} [cyan]{str(r.request_id):<24}[/] [dim]{str(r.received_at):<20}[/] '
                     f'[{style}]{glyph} {r.verdict.value:<5}[/] {str(r.rule_id):<4}  {path}')
    if not records:
        lines.append('  [dim](no records — run `sg sentinel local hit …`)[/]')
    lines += ['', '[dim][↑/↓] select   [enter] trace   [r] refresh   [?] help   [q] quit[/]']
    return '\n'.join(lines)


def trace_markup(record) -> str:
    if record is None:
        return '[red]no record for that request id[/]'
    glyph, style = _verdict_glyph(record.verdict.value)
    enforced = 'enforced' if record.enforced else 'passed to origin'
    return '\n'.join([
        f'[bold]Trace {record.request_id}[/]',
        '',
        f'  received_at  {record.received_at}',
        f'  request      {record.method} {str(record.path) or "(empty)"}   host={record.host}',
        f'  source_ip    {record.source_ip}  [dim](privacy mode applied)[/]',
        '',
        f'  [{style}]{glyph} {record.verdict.value}[/]  rule {record.rule_id} ({record.layer.value})  → {record.action.value}',
        f'  reason       {record.reason}',
        f'  enforcement  {enforced}  HTTP {record.http_status}',
        f'  engine       v{record.engine_version}  ruleset v{record.ruleset_version}',
        '',
        '[dim][esc] back   [q] quit[/]',
    ])


def logs_plain(records, sink_label: str) -> str:                                     # no-TTY fallback
    out = [f'SG/Sentinel logs (sink: {sink_label}):']
    for r in records:
        out.append(f'  {r.request_id}  {r.received_at}  {r.verdict.value:<5} {r.rule_id}  {str(r.path) or "(empty)"}')
    if not records:
        out.append('  (no records)')
    return '\n'.join(out)
