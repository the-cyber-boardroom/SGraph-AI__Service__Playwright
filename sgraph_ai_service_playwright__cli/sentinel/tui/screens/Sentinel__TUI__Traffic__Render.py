# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Traffic__Render
# Traffic surface content as Rich-markup strings. PURE — no textual/rich import; so
# it is unit-testable on 3.11. Shows the corpus + the last run's report (accuracy +
# latency) and a per-case results table (expected vs observed).
# ═══════════════════════════════════════════════════════════════════════════════


def _verdict_style(v: str) -> str:
    return 'red' if v == 'block' else 'green'


def traffic_markup(cases, report, results, running: bool = False) -> str:
    lines = ['[bold]SG/Sentinel — Traffic[/]  [dim](use-case generator + impact measurement)[/]', '']
    if running:
        lines.append('[yellow]running corpus through L1 + L2 …[/]')
        return '\n'.join(lines)

    benign    = sum(1 for c in cases if c.category.value == 'benign')
    malicious = sum(1 for c in cases if c.category.value == 'malicious')
    malformed = sum(1 for c in cases if c.category.value == 'malformed')
    lines.append(f'[bold]CORPUS[/]  {len(cases)} cases   '
                 f'[green]{benign} benign[/] / [red]{malicious} malicious[/] / [red]{malformed} malformed[/]')
    lines.append('')

    if report is None:
        lines += ['[dim]no run yet[/]', '',
                  '[dim][g] run in-process (L1+L2)   [r] reset   [?] help   [q] quit[/]']
        return '\n'.join(lines)

    acc_style = 'green' if report.accuracy_pct == 100.0 else 'yellow'
    lines.append(f'[bold]REPORT[/]  [dim](mode={report.mode})[/]')
    lines.append(f'  accuracy        [{acc_style}]{report.accuracy_pct}%[/]   '
                 f'([green]{report.allowed} allowed[/] / [red]{report.blocked} blocked[/] of {report.total})')
    lines.append(f'  malicious caught {report.malicious_blocked}/{report.malicious_total}'
                 f'      benign passed {report.benign_allowed}/{report.benign_total}')
    lines.append(f'  latency ms       min {report.latency_min_ms}  p50 {report.latency_p50_ms}  '
                 f'p95 {report.latency_p95_ms}  max {report.latency_max_ms}')
    lines.append('')
    lines.append('  [dim]CASE              CATEGORY   EXPECTED      OBSERVED      HTTP  ms[/]')
    for r in results:
        ok    = '[green]✓[/]' if r.matched else '[red]✗[/]'
        ov    = _verdict_style(r.observed_verdict.value)
        lines.append(f'  {ok} {str(r.name):<15} {r.category.value:<9} '
                     f'{r.expected_verdict.value}/{str(r.expected_rule):<5} '
                     f'[{ov}]{r.observed_verdict.value}/{str(r.observed_rule) or "?":<5}[/] '
                     f'{r.http_status:<4}  {round(r.latency_ms, 1)}')
    lines += ['', '[dim][g] run again   [r] reset   [?] help   [q] quit[/]']
    return '\n'.join(lines)


def traffic_plain(report, results) -> str:                                          # no-TTY fallback
    if report is None:
        return 'SG/Sentinel traffic: no run.'
    out = [f'SG/Sentinel traffic (mode={report.mode}): accuracy {report.accuracy_pct}%  '
           f'malicious_caught {report.malicious_blocked}/{report.malicious_total}  '
           f'benign_passed {report.benign_allowed}/{report.benign_total}  '
           f'latency p50 {report.latency_p50_ms}ms p95 {report.latency_p95_ms}ms']
    for r in results:
        out.append(f'  {"ok" if r.matched else "MISS"}  {r.name:<15} {r.expected_verdict.value}/{r.expected_rule}'
                   f' -> {r.observed_verdict.value}/{r.observed_rule or "?"}  {round(r.latency_ms, 1)}ms')
    return '\n'.join(out)
