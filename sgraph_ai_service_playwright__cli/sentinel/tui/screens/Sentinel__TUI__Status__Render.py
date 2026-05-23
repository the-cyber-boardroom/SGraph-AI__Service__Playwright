# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Status__Render
# Status / Deployed-code surface (mockups 1 + 7): locally-derivable reality plus the
# EXACT materialised L1 engine that ships to CloudFront (BANNED_IPS inlined). PURE —
# no textual/rich import; testable on 3.11. engine_code is raw text passed in, never
# fabricated. Live-AWS deployment status is read via `sg sentinel status` (hits AWS).
# ═══════════════════════════════════════════════════════════════════════════════


def status_markup(status, sink_label: str, engine_code: str) -> str:
    node = '[green]found[/]' if status.node_available else '[red]missing[/]'
    lines = ['[bold]SG/Sentinel — Status & Deployed Code[/]', '']
    lines += ['[bold]REALITY[/]',
              f'  engine        v{status.engine_version}   ruleset v{status.ruleset_version}',
              f'  rules         {status.rule_count}   [dim](tiny core, L1)[/]',
              f'  banned IPs    {status.banned_ip_count}   [dim](inlined into the engine)[/]',
              f'  node          {node}',
              f'  sink          {sink_label}',
              f'  records       {status.record_count}   '
              f'([green]{status.allow_count} allow[/] / [red]{status.block_count} block[/])',
              '']
    lines += ['[bold]L1 ENGINE — the exact code that ships to CloudFront[/]  [dim](BANNED_IPS inlined)[/]', '']
    for n, code_line in enumerate(engine_code.splitlines(), start=1):
        safe = code_line.replace('[', r'\[')                                         # escape Rich markup in source text
        lines.append(f'  [dim]{n:>3}[/] {safe}')
    lines += ['', '[dim][r] refresh   [?] help   [q] quit[/]']
    return '\n'.join(lines)


def status_plain(status, sink_label: str) -> str:                                    # no-TTY fallback (omits the full code dump)
    return '\n'.join([
        'SG/Sentinel status:',
        f'  engine v{status.engine_version}  ruleset v{status.ruleset_version}',
        f'  rules {status.rule_count}  banned_ips {status.banned_ip_count}  node {"found" if status.node_available else "missing"}',
        f'  sink {sink_label}',
        f'  records {status.record_count} (allow {status.allow_count} / block {status.block_count})',
    ])
