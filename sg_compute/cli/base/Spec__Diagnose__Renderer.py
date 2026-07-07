# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__Diagnose__Renderer
# Shared live boot-progress check-table. Driven by a service that exposes
# diagnose(region, name) yielding (check_name, status, detail) per boot stage, plus
# an external svc.health() probe. Renders into a rich.Live table that updates as
# each stage resolves — used by `create --wait` (via Spec__CLI__Builder._wait_healthy
# when the service has diagnose()), by the per-spec `check` / `wait` commands, and
# by anything else that wants the same surface.
#
# Generic by design: nothing here knows about any specific spec. Per-failure log-
# source suggestions are passed IN as a hints mapping + a log-command prefix, so the
# spec-specific `sg <spec> logs --source <x>` hints never leak into shared code.
#
# Not a Type_Safe: it holds rich.Table/Live objects and is pure CLI logic, matching
# Spec__CLI__Builder's own opt-out (Type_Safe's metaclass conflicts with this use).
# ═══════════════════════════════════════════════════════════════════════════════

import time

from rich.console import Console
from rich.live    import Live
from rich.table   import Table


DIAG_ICONS = {
    'ok'      : '[green]✓[/]',
    'fail'    : '[red]✗[/]',
    'warn'    : '[yellow]⚠[/]',
    'skip'    : '[dim]⊘[/]',
    'checking': '[dim]…[/]',
    'pending' : '[dim]·[/]',
}

DIAG_STATE_LABEL = {
    'ok'      : '[green]OK[/]',
    'fail'    : '[red]FAIL[/]',
    'warn'    : '[yellow]WARN[/]',
    'skip'    : '[dim]SKIP[/]',
    'checking': '[dim]…[/]',
    'pending' : '[dim]·[/]',
}

OK_STATES = ('ok', 'skip')                                                          # a row in one of these is "done, not a problem"


def build_check_table(rows, *, header_extra: str = '', ok_times: dict = None) -> Table:
    # ok_times (optional): {check_name: seconds-to-first-OK}. When passed (the
    # run_until_ok path), an 'OK@' column shows when each row first went green —
    # so a stuck poll makes it obvious which checks are still pending vs long done.
    show_ok = ok_times is not None
    t = Table(box=None, show_header=True, header_style='bold', padding=(0, 2), pad_edge=False)
    t.add_column('Check' , no_wrap=True, min_width=18)
    t.add_column('State' , no_wrap=True, min_width=6 )
    if show_ok:
        t.add_column('OK@', no_wrap=True, min_width=5)
    t.add_column('Detail' + (f'  [dim]{header_extra}[/]' if header_extra else ''))
    for name, status, detail in rows:
        icon  = DIAG_ICONS      .get(status, '[dim]?[/]')
        label = DIAG_STATE_LABEL.get(status, '[dim]?[/]')
        first_line, *_ = (detail or '').split('\n', 1)
        cells = [name, f'{icon} {label}']
        if show_ok:
            secs = ok_times.get(name)
            cells.append('' if secs is None else f'[green]{secs}s[/]')
        cells.append(f'[dim]{first_line}[/]')
        t.add_row(*cells)
    return t


def initial_rows(check_order) -> list:                                              # all rows up-front in 'pending' so the table doesn't grow top-down
    return [(n, 'pending', '') for n in (check_order or ())]                         # None/empty → rows grow as diagnose() yields


def probe_external_http(svc, region: str, name: str) -> tuple:                      # → (status, detail) for an external svc.health() probe
    try:
        result  = svc.health(region, name, timeout_sec=0)
        healthy = bool(getattr(result, 'healthy', False))
        state   = str (getattr(result, 'state', '') or '')
        err     = str (getattr(result, 'last_error', '') or '')
        elapsed = int (getattr(result, 'elapsed_ms', 0) or 0)
        if healthy:
            return ('ok', f'serving via health probe ({elapsed}ms)')
        if err:
            return ('warn', f'{state or "starting"} — {err}')
        return ('fail', state or 'no response')
    except Exception as exc:
        return ('fail', str(exc)[:160])


def run_checks(svc, region: str, name: str, *, live, rows: list, header_extra: str = '',
               ok_times: dict = None, started: float = None) -> list:
    # Drive svc.diagnose() + the external probe, updating `rows` (and the Live
    # table) in place. Returns the final rows list. Pure transport-free logic lives
    # in the service's diagnose() parsers; this just renders the stream.
    # ok_times/started (optional): stamp the elapsed seconds the first time a check
    # reaches an OK state, so the table can show a per-check time-to-OK column.
    by_name = {n: i for i, (n, _, _) in enumerate(rows)}

    def _set(check_name: str, status: str, detail: str):
        if check_name in by_name:
            rows[by_name[check_name]] = (check_name, status, detail)
        else:
            rows.append((check_name, status, detail))
            by_name[check_name] = len(rows) - 1
        if ok_times is not None and started is not None and status in OK_STATES \
                and check_name not in ok_times:
            ok_times[check_name] = int(time.monotonic() - started)                   # first-OK timestamp, kept even if it later flips
        live.update(build_check_table(rows, header_extra=header_extra, ok_times=ok_times))

    for check_name, status, detail in svc.diagnose(region, name):
        _set(check_name, status, detail)

    _set('external-http', 'checking', '')
    status, detail = probe_external_http(svc, region, name)
    _set('external-http', status, detail)
    return rows


def suggestions_for(rows, hints: dict, valid_sources=None) -> list:                 # de-duplicated log-source suggestions for any warn/fail row
    # hints: {check_name: [(source, reason), …]}. valid_sources (optional): only
    # suggest sources present in this set (so a hint can't name a non-existent
    # `logs --source`). Returns [(source, reason, origin_check), …].
    seen, out = set(), []
    for check_name, status, _ in rows:
        if status not in ('fail', 'warn'):
            continue
        for source, reason in (hints or {}).get(check_name, []):
            if valid_sources is not None and source not in valid_sources:
                continue
            if source not in seen:
                seen.add(source)
                out.append((source, reason, check_name))
    return out


def print_summary(c: Console, rows: list, name: str, *, hints: dict = None,
                  log_command_prefix: str = '', valid_sources=None) -> None:
    c.print()
    failed = [n for n, s, _ in rows if s == 'fail']
    warned = [n for n, s, _ in rows if s == 'warn']
    if not failed and not warned:
        c.print('  [green]✓  all checks passed[/]')
        c.print()
        return
    parts = []
    if failed: parts.append(f'[red]{len(failed)} failed[/]')
    if warned: parts.append(f'[yellow]{len(warned)} warnings[/]')
    c.print(f'  {", ".join(parts)}')
    # Suggestions are optional: only printed when the caller supplied a hints map
    # AND a log-command prefix (e.g. 'sg cp logs'). create --wait omits them unless
    # the cli_spec carries them; the per-spec check/wait commands always pass them.
    if hints and log_command_prefix:
        suggested = suggestions_for(rows, hints, valid_sources=valid_sources)
        if suggested:
            c.print()
            c.print('  [bold]Suggested next steps:[/]')
            for source, reason, origin in suggested:
                c.print(f'    [cyan]{log_command_prefix} {name} --source {source:<13}[/]'
                        f'  [dim]# {reason}  ({origin})[/]')
    c.print()


def run_once(svc, region: str, name: str, *, console: Console, check_order,
             hints: dict = None, log_command_prefix: str = '', valid_sources=None,
             title: str = 'Checks') -> list:
    # One-shot: render the live table once, print the summary. Returns final rows.
    console.print()
    console.print(f'  [bold]{title}[/]  ·  [cyan]{name}[/]  [dim]{region}[/]')
    console.print()
    rows = initial_rows(check_order)
    with Live(build_check_table(rows), console=console, refresh_per_second=8, transient=False) as live:
        run_checks(svc, region, name, live=live, rows=rows)
    print_summary(console, rows, name, hints=hints, log_command_prefix=log_command_prefix,
                  valid_sources=valid_sources)
    return rows


def run_until_ok(svc, region: str, name: str, *, console: Console, check_order,
                 timeout: int, poll: int, hints: dict = None, log_command_prefix: str = '',
                 valid_sources=None, title: str = 'Waiting') -> tuple:
    # Loop the live table until every row is ok/skip or timeout. Returns
    # (rows, all_ok). The caller decides exit semantics from all_ok.
    console.print()
    console.print(f'  [bold]{title}[/]  ·  [cyan]{name}[/]  [dim]{region}[/]  '
                  f'[dim](timeout={timeout}s, poll={poll}s)[/]')
    console.print()
    rows     = initial_rows(check_order)
    ok_times = {}                                                                    # {check_name: seconds-to-first-OK} → the OK@ column
    started  = time.monotonic()
    attempt  = 0
    all_ok   = False
    with Live(build_check_table(rows, ok_times=ok_times), console=console, refresh_per_second=8, transient=False) as live:
        while True:
            attempt += 1
            elapsed  = int(time.monotonic() - started)
            header   = f'attempt={attempt}  elapsed={elapsed}s'
            run_checks(svc, region, name, live=live, rows=rows, header_extra=header,
                       ok_times=ok_times, started=started)
            all_ok = all(s in OK_STATES for _, s, _ in rows)
            if all_ok or time.monotonic() - started >= timeout:
                break
            time.sleep(poll)
    print_summary(console, rows, name, hints=hints, log_command_prefix=log_command_prefix,
                  valid_sources=valid_sources)
    return rows, all_ok
